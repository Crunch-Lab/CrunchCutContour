#!/usr/bin/env python3
"""Éditeur interactif : affiche un EPS dans le navigateur et laisse choisir au clic
les tracés à passer en magenta pur, puis enregistre en magenta ou en CutContour.

Un petit serveur HTTP local (127.0.0.1, port aléatoire, jeton secret) sert la page
et reçoit l'ordre d'enregistrement ; aucune dépendance hors bibliothèque standard.
"""

import base64
import http.server
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import urllib.parse
import webbrowser

import eps_cutcontour as conv
import eps_interpreteur as interp

MAGENTA = "1 0 1 setrgbcolor"
CUT_WIDTH = 0.25  # épaisseur (pt) du contour ajouté autour d'un aplat


def fmt(v):
    return f"{v:.3f}".rstrip("0").rstrip(".") or "0"


def is_magenta(rgb, tolerance):
    return all(abs(a - b) <= tolerance for a, b in zip(rgb, (1.0, 0.0, 1.0)))


def svg_path(segments):
    out = []
    for seg in segments:
        if seg[0] == "Z":
            out.append("Z")
        else:
            out.append(seg[0] + " ".join(f"{fmt(x)} {fmt(y)}" for x, y in seg[1:]))
    return "".join(out)


def apply_selection(text, paints, selection):
    """Passe en magenta pur chaque tracé choisi, en entourant l'instruction qui le peint.

    Un trait est simplement recoloré ; un aplat garde sa couleur et reçoit un
    contour magenta fin, tracé par-dessus.
    """
    edits = []
    for i in sorted(set(selection)):
        p = paints[i]
        start, end = p.span
        op = text[start:end]
        if p.kind == "stroke":
            new = f"gsave {MAGENTA} {op} grestore newpath"
        elif p.kind == "rectstroke":
            new = f"gsave {MAGENTA} {op} grestore"
        else:
            new = (f"gsave {op} grestore gsave {MAGENTA} {fmt(CUT_WIDTH / p.scale)} setlinewidth "
                   f"[] 0 setdash stroke grestore newpath")
        edits.append((start, end, new))
    parts, last = [], 0
    for start, end, new in sorted(edits):
        parts += [text[last:start], new]
        last = end
    parts.append(text[last:])
    return "".join(parts)


class Editeur:
    """Un document ouvert. directory vaut None pour un fichier déposé dans le navigateur :
    on ne connaît alors pas son dossier et le résultat est renvoyé en téléchargement."""

    def __init__(self, data, name, directory, spot_name, tolerance):
        self.name = os.path.basename(name) or "fichier.eps"
        self.directory = directory
        self.spot_name, self.tolerance = spot_name, tolerance
        self.dos_parts = conv.split_dos_eps(data)
        ps_bytes = self.dos_parts[0] if self.dos_parts else data
        if not ps_bytes.startswith(b"%!PS"):
            raise ValueError(f"« {self.name} » n'est pas un fichier EPS (il ne commence pas par %!PS).")
        self.text = ps_bytes.decode("latin-1")
        self.paints, self.error = interp.interpret(self.text)
        if not self.paints:
            raise ValueError(f"Aucun tracé lisible dans « {self.name} »" +
                             (f" ({self.error})." if self.error else "."))

    @classmethod
    def from_path(cls, path, spot_name, tolerance):
        path = os.path.abspath(path)
        with open(path, "rb") as fh:
            data = fh.read()
        return cls(data, path, os.path.dirname(path), spot_name, tolerance)

    def magenta(self, p):
        return p.spot == self.spot_name or is_magenta(p.rgb, self.tolerance)

    def page(self, token):
        base = os.path.splitext(self.name)[0]
        bbox = interp.bounding_box(self.text)
        if bbox is None:
            pts = [pt for p in self.paints for seg in p.segments for pt in seg[1:]]
            bbox = (min(x for x, _ in pts), min(y for _, y in pts),
                    max(x for x, _ in pts), max(y for _, y in pts))
        traces = [{
            "k": p.kind,
            "d": svg_path(p.segments),
            "c": "#%02X%02X%02X" % tuple(round(v * 255) for v in p.rgb),
            "w": round(p.width, 3),
            "e": p.editable,
            "m": self.magenta(p),
            "s": p.spot,
        } for p in self.paints]
        donnees = {
            "fichier": self.name,
            "bbox": bbox,
            "traces": traces,
            "erreur": self.error,
            "jeton": token,
            "telechargement": self.directory is None,
            "ton": self.spot_name,
            "noms": {"cutcontour": f"{base}_{self.spot_name}.eps", "magenta": f"{base}_magenta.eps"},
        }
        payload = json.dumps(donnees, ensure_ascii=False).replace("</", "<\\/")
        return fill_page(PAGE, token).replace("__DONNEES__", payload)

    def save(self, selection, mode, name):
        if mode not in ("cutcontour", "magenta"):
            return {"ok": False, "message": "Mode d'enregistrement inconnu."}
        if not isinstance(name, str) or not re.fullmatch(r"[^/\\:*?\"<>|\0]+\.eps", name, re.I) \
                or name in (".eps", "..eps"):
            return {"ok": False, "message": "Nom de fichier invalide : un simple nom terminé par .eps."}
        out = os.path.join(self.directory, name) if self.directory else None
        if name == self.name:
            return {"ok": False, "message": "Le fichier de sortie doit avoir un autre nom que le fichier ouvert."}

        chosen = {i for i in selection if isinstance(i, int) and 0 <= i < len(self.paints)
                  and self.paints[i].editable and self.paints[i].spot != self.spot_name}
        if mode == "magenta":
            chosen = {i for i in chosen if not self.magenta(self.paints[i])}
            if not chosen:
                return {"ok": False, "message": "Aucun nouveau tracé sélectionné : rien à enregistrer."}
        text = apply_selection(self.text, self.paints, chosen)
        if mode == "cutcontour":
            text, count, _ = conv.convert_text(text, self.spot_name, self.tolerance)
            if count == 0:
                return {"ok": False, "message": "Aucun tracé à convertir : rien à enregistrer."}

        # Vérification : le fichier produit doit se relire, avec au moins autant de tracés magenta.
        check, error = interp.interpret(text)
        if error and not self.error:
            return {"ok": False, "message": f"Le fichier produit ne se relit pas ({error}) : rien n'a été écrit."}
        expected = len(chosen | {i for i, p in enumerate(self.paints) if self.magenta(p)})
        if sum(1 for p in check if self.magenta(p)) < expected:
            return {"ok": False, "message": "Vérification échouée : certains tracés ne sont pas passés "
                                            "en magenta. Rien n'a été écrit."}

        data = text.encode("latin-1")
        if self.dos_parts:
            data = conv.join_dos_eps(data, *self.dos_parts[1:])
        label = self.spot_name if mode == "cutcontour" else "magenta pur"
        if out is None:
            return {"ok": True, "nom": name, "donnees": base64.b64encode(data).decode("ascii"),
                    "message": f"Téléchargé ({label}) : {name}"}
        existed = os.path.exists(out)
        with open(out, "wb") as fh:
            fh.write(data)
        return {"ok": True, "chemin": out,
                "message": f"Enregistré ({label}{', fichier remplacé' if existed else ''}) : {out}"}


MAX_UPLOAD = 200 * 1024 * 1024


class Application:
    """État du serveur : le document ouvert (ou aucun, en attente d'un dépôt)."""

    def __init__(self, spot_name, tolerance):
        self.spot_name, self.tolerance = spot_name, tolerance
        self.token = secrets.token_urlsafe(16)
        self.ed = None

    def open_bytes(self, data, name):
        try:
            ed = Editeur(data, name, None, self.spot_name, self.tolerance)
        except ValueError as e:
            return {"ok": False, "message": str(e)}
        self.ed = ed
        print(f"{len(ed.paints)} tracé(s) lus dans {ed.name} (déposé dans le navigateur).")
        return {"ok": True}

    def page(self):
        return self.ed.page(self.token) if self.ed else fill_page(PAGE_DEPOT, self.token)


def fill_page(template, token):
    return (template.replace("__STYLE__", STYLE).replace("__DEPOT_JS__", DEPOT_JS)
            .replace("__JETON__", json.dumps(token)))


def make_handler(app):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/" + app.token:
                self._send(200, app.page().encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._send(404, "Page introuvable".encode(), "text/plain; charset=utf-8")

        def _json(self, result):
            self._send(200, json.dumps(result, ensure_ascii=False).encode("utf-8"), "application/json")

        def do_POST(self):
            if self.headers.get("X-Jeton") != app.token:
                self._send(403, b"{}", "application/json")
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 <= length <= MAX_UPLOAD:
                self._json({"ok": False, "message": "Fichier trop volumineux ou requête invalide."})
                return
            raw = self.rfile.read(length)
            if self.path == "/api/ouvrir":
                self._json(app.open_bytes(raw, urllib.parse.unquote(self.headers.get("X-Nom") or "")))
                return
            try:
                body = json.loads(raw or b"{}")
            except ValueError:
                self._send(400, b"{}", "application/json")
                return
            if self.path == "/api/enregistrer":
                if app.ed is None:
                    result = {"ok": False, "message": "Aucun fichier ouvert."}
                else:
                    result = app.ed.save(body.get("selection") or [], body.get("mode"), body.get("nom"))
            elif self.path == "/api/quitter":
                result = {"ok": True}
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self._send(404, b"{}", "application/json")
                return
            self._json(result)

    return Handler


def _windows_default_is_ie():
    """Vrai si le navigateur par défaut est Internet Explorer (cas courant sous Windows 7)."""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations"
                            r"\UrlAssociations\http\UserChoice") as k:
            return winreg.QueryValueEx(k, "ProgId")[0].upper().startswith("IE.")
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"http\shell\open\command") as k:
            return "iexplore" in winreg.QueryValueEx(k, "")[0].lower()
    except OSError:
        return False


def _modern_browsers():
    """Chrome, Firefox ou Edge installés, dans cet ordre."""
    roots = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "LOCALAPPDATA")]
    names = [r"Google\Chrome\Application\chrome.exe", r"Mozilla Firefox\firefox.exe",
             r"Microsoft\Edge\Application\msedge.exe"]
    found = [os.path.join(r, n) for n in names for r in roots if r and os.path.isfile(os.path.join(r, n))]
    return list(dict.fromkeys(os.path.normcase(p) for p in found))


def open_browser(url):
    """Ouvre l'URL ; sous WSL, dans le navigateur de Windows ; jamais dans Internet Explorer."""
    if sys.platform == "win32" and _windows_default_is_ie():
        for exe in _modern_browsers():
            try:
                subprocess.Popen([exe, url])
                return
            except OSError:
                pass
        print("Internet Explorer ne peut pas afficher l'éditeur : ouvrez l'adresse ci-dessus "
              "dans Chrome, Firefox ou Edge.")
        return
    try:
        with open("/proc/version") as fh:
            wsl = "microsoft" in fh.read().lower()
    except OSError:
        wsl = False
    if wsl:
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "", url], cwd="/mnt/c" if os.path.isdir("/mnt/c") else None,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except OSError:
            pass
    webbrowser.open(url)


def run(path=None, spot_name="CutContour", tolerance=0.002, browser=True, port=0):
    """Lance l'éditeur ; sans `path`, la page attend qu'on y dépose un fichier EPS."""
    try:
        sys.stdout.reconfigure(line_buffering=True)  # l'adresse s'affiche même si la sortie est redirigée
    except (AttributeError, ValueError):
        pass
    app = Application(spot_name, tolerance)
    if path:
        try:
            app.ed = Editeur.from_path(path, spot_name, tolerance)
        except (OSError, ValueError) as e:
            sys.exit(f"Erreur : {e}")
        if app.ed.error:
            print(f"Attention : lecture incomplète du fichier ({app.ed.error}).", file=sys.stderr)
        print(f"{len(app.ed.paints)} tracé(s) lus dans {app.ed.name}.")
    else:
        print("Aucun fichier indiqué : déposez un fichier EPS dans la page du navigateur.")

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    url = f"http://127.0.0.1:{server.server_address[1]}/{app.token}"
    print(f"Éditeur ouvert sur : {url}")
    print("Gardez cette fenêtre ouverte pendant l'utilisation.")
    print("Ctrl+C ou le bouton « Quitter » pour arrêter.")
    if browser:
        open_browser(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


STYLE = r""":root {
  --fond: #eef0f3; --barre: #ffffff; --texte: #1d2330; --doux: #5d6675; --bord: #d5d9e0;
  --accent: #c2008f; --accent-texte: #ffffff; --survol: #0091ff; --erreur: #b3261e; --ok: #1e7b34;
}
@media (prefers-color-scheme: dark) {
  :root { --fond: #16181d; --barre: #20232a; --texte: #e6e8ec; --doux: #9aa1ad; --bord: #343844;
          --accent: #ff4fd1; --accent-texte: #1a0014; --erreur: #ff8a80; --ok: #7ad38f; }
}
* { box-sizing: border-box; }
html, body { height: 100%; margin: 0; }
body { display: flex; flex-direction: column; background: var(--fond); color: var(--texte);
       font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; padding: 10px 16px;
         background: var(--barre); border-bottom: 1px solid var(--bord); }
h1 { font-size: 15px; margin: 0; font-weight: 600; }
h1 small { font-weight: 400; color: var(--doux); }
.groupe { display: flex; align-items: center; gap: 6px; }
.espace { flex: 1; }
button, input[type=text] { font: inherit; color: var(--texte); background: var(--fond);
       border: 1px solid var(--bord); border-radius: 6px; padding: 5px 10px; }
button { cursor: pointer; }
button:hover { border-color: var(--doux); }
button.principal { background: var(--accent); color: var(--accent-texte); border-color: var(--accent); font-weight: 600; }
input[type=text] { width: 230px; }
label { cursor: pointer; }
#zone { flex: 1; overflow: auto; display: flex; padding: 24px; }
#papier { margin: auto; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.25); line-height: 0; }
svg { display: block; }
.cible { cursor: pointer; }
.cible.bloque { cursor: not-allowed; }
footer { display: flex; gap: 16px; align-items: center; padding: 8px 16px; background: var(--barre);
         border-top: 1px solid var(--bord); min-height: 38px; }
#info { color: var(--doux); flex: 1; }
#message.ok { color: var(--ok); } #message.erreur { color: var(--erreur); }
#alerte { display: none; padding: 8px 16px; background: #fff4e5; color: #6b3d00; border-bottom: 1px solid #f0c27b; }
#legende { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 20px; padding: 6px 16px;
           background: var(--barre); border-bottom: 1px solid var(--bord); color: var(--doux); }
#legende .item { display: flex; align-items: center; gap: 6px; }
#legende svg { background: #fff; border: 1px solid var(--bord); border-radius: 3px; }
#legende b { color: var(--texte); font-variant-numeric: tabular-nums; }
#notification { position: fixed; top: 72px; left: 50%; transform: translate(-50%, -12px); max-width: min(640px, calc(100% - 32px));
                padding: 12px 18px; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,.25); color: #fff;
                font-weight: 600; opacity: 0; pointer-events: none; transition: opacity .2s, transform .2s; z-index: 10; }
#notification.visible { opacity: 1; transform: translate(-50%, 0); pointer-events: auto; }
#notification.ok { background: #1e7b34; }
#notification.erreur { background: #b3261e; }
#notification small { display: block; font-weight: 400; opacity: .9; word-break: break-all; margin-top: 2px; }
#voile-depot { display: none; position: fixed; inset: 0; z-index: 20; align-items: center; justify-content: center;
               background: rgba(194, 0, 143, .12); border: 3px dashed var(--accent); font-size: 20px; font-weight: 600;
               color: var(--accent); pointer-events: none; }
body.depot-survol #voile-depot { display: flex; }
#depot { flex: 1; display: flex; align-items: center; justify-content: center; padding: 24px 16px; }
#cadre-depot { width: min(560px, 100%); padding: 48px 24px; text-align: center; border: 2px dashed var(--bord);
               border-radius: 14px; background: var(--barre); transition: border-color .15s, background .15s; }
body.depot-survol #cadre-depot { border-color: var(--accent); }
#cadre-depot h2 { margin: 0 0 6px; font-size: 20px; }
#cadre-depot p { margin: 0 0 18px; color: var(--doux); }
#etat-depot { margin-top: 18px; min-height: 1.4em; }
#etat-depot.erreur { color: var(--erreur); font-weight: 600; }
"""

PAGE = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Éditeur CutContour</title>
<style>
__STYLE__
</style>
</head>
<body>
<script>
/* Écrit en ES3 : doit s'exécuter même dans un navigateur trop ancien pour l'éditeur. */
if (!window.fetch || !window.Promise || !("noModule" in document.createElement("script"))) {
  document.write('<div style="padding:16px;margin:16px;border:2px solid #b3261e;background:#fff;color:#b3261e;font:16px sans-serif">' +
    "Ce navigateur est trop ancien pour l'éditeur (Internet Explorer n'est pas pris en charge).<br>" +
    "Ouvrez cette adresse dans Chrome, Firefox ou Edge :<br><b>" + location.href + "</b></div>");
}
</script>
<header>
  <h1>Éditeur CutContour <small id="fichier"></small></h1>
  <div class="groupe">
    <button id="moins" title="Zoom arrière">−</button>
    <button id="ajuster">Ajuster</button>
    <button id="plus" title="Zoom avant">+</button>
  </div>
  <button id="aucun">Tout désélectionner</button>
  <button id="ouvrir" title="Ou déposez un fichier EPS n'importe où dans la page">Ouvrir un autre fichier…</button>
  <input type="file" id="choisir" accept=".eps,.epsf,.ps" hidden>
  <span class="espace"></span>
  <div class="groupe">
    <label><input type="radio" name="mode" value="cutcontour" checked> <span id="nom-ton"></span></label>
    <label><input type="radio" name="mode" value="magenta"> Magenta pur</label>
  </div>
  <div class="groupe">
    <input type="text" id="nom" spellcheck="false" aria-label="Nom du fichier de sortie">
    <button class="principal" id="enregistrer">Enregistrer</button>
    <button id="quitter">Quitter</button>
  </div>
</header>
<div id="legende">
  <span class="item">
    <svg width="34" height="14"><path d="M3 7H31" stroke="#FF00FF" stroke-width="2.5"/></svg>
    Coupe d'origine <b id="n-origine">0</b>
  </span>
  <span class="item">
    <svg width="34" height="14"><path d="M3 7H31" stroke="#FF00FF" stroke-width="2.5"/>
      <path d="M3 7H31" stroke="#fff" stroke-width="1" stroke-dasharray="4 4"/></svg>
    Coupe ajoutée <b id="n-ajoutee">0</b>
  </span>
  <span class="item">
    <svg width="34" height="14"><path d="M3 7H31" stroke="#7A8190" stroke-width="1.2" stroke-dasharray="1 3"/></svg>
    Non modifiable <b id="n-bloque">0</b>
  </span>
  <label class="item"><input type="checkbox" id="estomper"> Estomper le dessin</label>
</div>
<div id="alerte"></div>
<div id="notification" role="status" aria-live="polite"></div>
<div id="voile-depot">Déposez le fichier EPS pour l'ouvrir</div>
<div id="zone"><div id="papier"><svg id="dessin" xmlns="http://www.w3.org/2000/svg"></svg></div></div>
<footer>
  <span id="info"></span>
  <span id="message"></span>
</footer>
<script id="donnees" type="application/json">__DONNEES__</script>
<script>
"use strict";
const D = JSON.parse(document.getElementById("donnees").textContent);
const NS = "http://www.w3.org/2000/svg";
const MAGENTA = "#FF00FF";
const $ = id => document.getElementById(id);

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

$("fichier").textContent = "— " + D.fichier;
$("nom-ton").textContent = D.ton;
if (D.erreur) {
  $("alerte").style.display = "block";
  $("alerte").textContent = "Lecture incomplète du fichier (" + D.erreur +
    "). Les tracés affichés restent utilisables.";
}

const [x0, y0, x1, y1] = D.bbox;
const W = x1 - x0, H = y1 - y0;
const svg = $("dessin");
svg.setAttribute("viewBox", `${x0} ${-y1} ${W} ${H}`);
const racine = el("g", {transform: "scale(1,-1)"}, svg);
const gRendu = el("g", {"pointer-events": "none"}, racine);
const gBloques = el("g", {"pointer-events": "none", display: "none"}, racine);
const gContours = el("g", {"pointer-events": "none"}, racine);
const gSurvol = el("g", {"pointer-events": "none"}, racine);
const gCibles = el("g", {}, racine);

const selection = new Set();
const rendus = [], contours = [];

D.traces.forEach((t, i) => {
  let r;
  if (t.k === "stroke" || t.k === "rectstroke") {
    const w = t.w > 0.05 ? {"stroke-width": t.w} : {"stroke-width": 1, "vector-effect": "non-scaling-stroke"};
    r = el("path", {d: t.d, fill: "none", stroke: t.c, ...w}, gRendu);
  } else if (t.k === "image") {
    r = el("path", {d: t.d, fill: "#9aa1ad", "fill-opacity": 0.35}, gRendu);
  } else {
    r = el("path", {d: t.d, fill: t.c, "fill-rule": t.k === "eofill" ? "evenodd" : "nonzero"}, gRendu);
  }
  rendus[i] = r;
  if (t.m) selection.add(i);
  if (!t.e && !t.m && t.k !== "image") {
    el("path", {d: t.d, fill: "none", stroke: "#7A8190", "stroke-width": 1.2, "stroke-dasharray": "1 3",
                "vector-effect": "non-scaling-stroke"}, gBloques);
  }
});
const nBloques = D.traces.filter(t => !t.e && !t.m && t.k !== "image").length;
const nOrigine = D.traces.filter(t => t.m).length;

// Cibles de clic : les aplats d'abord, les traits par-dessus pour qu'ils restent faciles à attraper.
const ordre = D.traces.map((t, i) => i).filter(i => D.traces[i].k !== "image");
ordre.sort((a, b) => estTrait(a) - estTrait(b));
for (const i of ordre) {
  const t = D.traces[i];
  const attrs = estTrait(i)
    ? {d: t.d, fill: "none", stroke: "#000", "stroke-opacity": 0, "stroke-width": 10,
       "vector-effect": "non-scaling-stroke", "pointer-events": "stroke"}
    : {d: t.d, fill: "#000", "fill-opacity": 0, "pointer-events": "fill",
       "fill-rule": t.k === "eofill" ? "evenodd" : "nonzero"};
  const c = el("path", attrs, gCibles);
  c.classList.add("cible");
  if (!t.e && !t.m) c.classList.add("bloque");
  c.addEventListener("mouseenter", () => survoler(i));
  c.addEventListener("mouseleave", () => survoler(null));
  c.addEventListener("click", () => basculer(i));
}

function estTrait(i) { const k = D.traces[i].k; return k === "stroke" || k === "rectstroke" ? 1 : 0; }

// Repère de coupe : magenta continu pour une coupe d'origine, avec pointillés blancs pour une coupe ajoutée.
function dessinerEtat(i) {
  const t = D.traces[i], choisi = selection.has(i);
  if (estTrait(i)) rendus[i].setAttribute("stroke", choisi ? MAGENTA : t.c);
  if (contours[i]) { contours[i].remove(); contours[i] = null; }
  if (!choisi) return;
  const g = el("g", {}, gContours);
  el("path", {d: t.d, fill: "none", stroke: MAGENTA, "stroke-width": 2.5, "stroke-linejoin": "round",
              "vector-effect": "non-scaling-stroke"}, g);
  if (!t.m) {
    el("path", {d: t.d, fill: "none", stroke: "#fff", "stroke-width": 1, "stroke-dasharray": "4 4",
                "vector-effect": "non-scaling-stroke"}, g);
  }
  contours[i] = g;
}

function basculer(i) {
  const t = D.traces[i];
  if (t.m) { message("Ce tracé est déjà en magenta pur dans le fichier.", ""); return; }
  if (!t.e) { message("Ce tracé ne peut pas être modifié seul : il est peint par une instruction partagée avec d'autres.", "erreur"); return; }
  if (selection.has(i)) selection.delete(i); else selection.add(i);
  dessinerEtat(i);
  majInfo();
  survoler(i);
}

let survolActuel = null;
function survoler(i) {
  if (survolActuel) { survolActuel.remove(); survolActuel = null; }
  if (i === null) { majInfo(); return; }
  const t = D.traces[i];
  survolActuel = el("path", {d: t.d, fill: "none", stroke: "#0091FF", "stroke-width": 2,
                             "stroke-dasharray": "5 3", "vector-effect": "non-scaling-stroke"}, gSurvol);
  const type = estTrait(i) ? `trait de ${String(t.w).replace(".", ",")} pt` : "aplat";
  const couleur = t.s ? `ton direct ${t.s}` : t.c;
  const etat = t.m ? "coupe d'origine (déjà dans le fichier)" : !t.e ? "non modifiable"
             : selection.has(i) ? "coupe ajoutée — cliquer pour annuler"
             : estTrait(i) ? "cliquer pour le passer en magenta" : "cliquer pour lui ajouter un contour magenta";
  $("info").textContent = `Tracé n°${i + 1} — ${type} — ${couleur} — ${etat}`;
}

function majInfo() {
  $("n-origine").textContent = nOrigine;
  $("n-ajoutee").textContent = selection.size - nOrigine;
  $("n-bloque").textContent = nBloques;
  $("info").textContent = `${D.traces.length} tracés. ` +
    "Cliquez sur un contour pour le passer en magenta pur ; recliquez pour annuler.";
}

$("estomper").addEventListener("change", e => {
  gRendu.setAttribute("opacity", e.target.checked ? 0.25 : 1);
  gBloques.setAttribute("display", e.target.checked ? "inline" : "none");
});

for (let i = 0; i < D.traces.length; i++) dessinerEtat(i);
majInfo();

// Zoom
let zoom = 1;
function appliquerZoom() {
  svg.setAttribute("width", Math.max(1, W * zoom));
  svg.setAttribute("height", Math.max(1, H * zoom));
}
function ajuster() {
  const zone = $("zone");
  zoom = Math.max(0.05, Math.min((zone.clientWidth - 48) / W, (zone.clientHeight - 48) / H));
  appliquerZoom();
}
$("plus").onclick = () => { zoom *= 1.25; appliquerZoom(); };
$("moins").onclick = () => { zoom /= 1.25; appliquerZoom(); };
$("ajuster").onclick = ajuster;
$("zone").addEventListener("wheel", e => {
  if (!e.ctrlKey) return;
  e.preventDefault();
  zoom *= e.deltaY < 0 ? 1.1 : 1 / 1.1;
  appliquerZoom();
}, {passive: false});
window.addEventListener("resize", ajuster);
ajuster();

$("aucun").onclick = () => {
  for (const i of [...selection]) if (!D.traces[i].m) { selection.delete(i); dessinerEtat(i); }
  majInfo();
};

// Nom de sortie : suit le mode tant que l'utilisateur ne l'a pas modifié.
let nomModifie = false;
const modeCourant = () => document.querySelector("input[name=mode]:checked").value;
$("nom").value = D.noms[modeCourant()];
$("nom").addEventListener("input", () => { nomModifie = true; });
document.querySelectorAll("input[name=mode]").forEach(r => r.addEventListener("change", () => {
  if (!nomModifie) $("nom").value = D.noms[modeCourant()];
}));

function message(texte, classe) {
  const m = $("message");
  m.textContent = texte;
  m.className = classe || "";
}

let minuterieNotification = null;
function notifier(titre, detail, classe) {
  const n = $("notification");
  n.textContent = titre;
  if (detail) { const s = document.createElement("small"); s.textContent = detail; n.appendChild(s); }
  n.className = "visible " + classe;
  clearTimeout(minuterieNotification);
  minuterieNotification = setTimeout(() => { n.className = classe; }, classe === "ok" ? 5000 : 8000);
}
$("notification").addEventListener("click", () => { $("notification").className = ""; });

function telecharger(nom, base64) {
  const octets = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
  const url = URL.createObjectURL(new Blob([octets], {type: "application/postscript"}));
  const a = document.createElement("a");
  a.href = url;
  a.download = nom;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

const JETON = __JETON__;
function signalerDepot(texte, erreur) {
  if (erreur) notifier("Fichier non ouvert", texte, "erreur"); else message(texte, "");
}
$("ouvrir").onclick = () => $("choisir").click();
__DEPOT_JS__

async function appeler(chemin, corps) {
  const r = await fetch(chemin, {method: "POST", headers: {"Content-Type": "application/json", "X-Jeton": D.jeton},
                                 body: JSON.stringify(corps || {})});
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

$("enregistrer").onclick = async () => {
  message("Enregistrement…", "");
  try {
    const res = await appeler("/api/enregistrer", {selection: [...selection], mode: modeCourant(), nom: $("nom").value.trim()});
    message(res.message, res.ok ? "ok" : "erreur");
    if (res.ok && res.donnees) {
      telecharger(res.nom, res.donnees);
      notifier("✓ Fichier bien enregistré", `${res.nom} — dans le dossier de téléchargement du navigateur`, "ok");
    } else if (res.ok) {
      notifier("✓ Fichier bien enregistré", res.chemin, "ok");
    } else {
      notifier("Fichier non enregistré", res.message, "erreur");
    }
  } catch (e) {
    message("Le serveur ne répond pas (" + e.message + ").", "erreur");
    notifier("Fichier non enregistré", "Le serveur ne répond pas (" + e.message + ").", "erreur");
  }
};

$("quitter").onclick = async () => {
  try { await appeler("/api/quitter"); } catch (e) { /* serveur déjà arrêté */ }
  document.body.innerHTML = "<p style='padding:24px'>Éditeur arrêté. Vous pouvez fermer cet onglet.</p>";
};
</script>
</body>
</html>
"""


# Dépôt de fichier, commun à la page d'attente et à l'éditeur. La page définit JETON et
# signalerDepot(texte, erreur) ; un champ <input type=file id="choisir"> est facultatif.
DEPOT_JS = r"""
async function ouvrirFichier(fichier) {
  if (!fichier) return;
  if (!/\.(eps|epsf|ps)$/i.test(fichier.name)) {
    signalerDepot(`« ${fichier.name} » n'est pas un fichier EPS (extension .eps attendue).`, true);
    return;
  }
  signalerDepot(`Lecture de « ${fichier.name} »…`, false);
  try {
    const r = await fetch("/api/ouvrir", {method: "POST", body: fichier,
      headers: {"X-Jeton": JETON, "X-Nom": encodeURIComponent(fichier.name)}});
    const res = await r.json();
    if (res.ok) location.reload(); else signalerDepot(res.message, true);
  } catch (e) {
    signalerDepot("Le serveur ne répond pas (" + e.message + ").", true);
  }
}
let profondeurDepot = 0;
window.addEventListener("dragenter", e => {
  e.preventDefault();
  if (++profondeurDepot === 1) document.body.classList.add("depot-survol");
});
window.addEventListener("dragleave", () => {
  if (--profondeurDepot <= 0) { profondeurDepot = 0; document.body.classList.remove("depot-survol"); }
});
window.addEventListener("dragover", e => e.preventDefault());
window.addEventListener("drop", e => {
  e.preventDefault();
  profondeurDepot = 0;
  document.body.classList.remove("depot-survol");
  const fichiers = e.dataTransfer && e.dataTransfer.files;
  if (fichiers && fichiers.length > 1) signalerDepot("Un seul fichier à la fois : seul le premier est ouvert.", false);
  ouvrirFichier(fichiers && fichiers[0]);
});
const champFichier = document.getElementById("choisir");
if (champFichier) champFichier.addEventListener("change", () => ouvrirFichier(champFichier.files[0]));
"""


PAGE_DEPOT = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Éditeur CutContour</title>
<style>
__STYLE__
</style>
</head>
<body>
<script>
/* Écrit en ES3 : doit s'exécuter même dans un navigateur trop ancien pour l'éditeur. */
if (!window.fetch || !window.Promise || !("noModule" in document.createElement("script"))) {
  document.write('<div style="padding:16px;margin:16px;border:2px solid #b3261e;background:#fff;color:#b3261e;font:16px sans-serif">' +
    "Ce navigateur est trop ancien pour l'éditeur (Internet Explorer n'est pas pris en charge).<br>" +
    "Ouvrez cette adresse dans Chrome, Firefox ou Edge :<br><b>" + location.href + "</b></div>");
}
</script>
<header>
  <h1>Éditeur CutContour</h1>
  <span class="espace"></span>
  <button id="quitter">Quitter</button>
</header>
<main id="depot">
  <div id="cadre-depot">
    <h2>Déposez un fichier EPS ici</h2>
    <p>Glissez-le depuis l'explorateur de fichiers, ou choisissez-le.</p>
    <button class="principal" id="parcourir">Choisir un fichier…</button>
    <input type="file" id="choisir" accept=".eps,.epsf,.ps" hidden>
    <div id="etat-depot" role="status" aria-live="polite"></div>
  </div>
</main>
<script>
"use strict";
const JETON = __JETON__;
function signalerDepot(texte, erreur) {
  const etat = document.getElementById("etat-depot");
  etat.textContent = texte;
  etat.className = erreur ? "erreur" : "";
}
document.getElementById("parcourir").onclick = () => document.getElementById("choisir").click();
document.getElementById("quitter").onclick = async () => {
  try {
    await fetch("/api/quitter", {method: "POST", headers: {"X-Jeton": JETON}, body: "{}"});
  } catch (e) { /* serveur déjà arrêté */ }
  document.body.innerHTML = "<p style='padding:24px'>Éditeur arrêté. Vous pouvez fermer cet onglet.</p>";
};
__DEPOT_JS__
</script>
</body>
</html>
"""
