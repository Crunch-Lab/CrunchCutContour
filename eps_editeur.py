#!/usr/bin/env python3
# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
"""Éditeur interactif : affiche un EPS dans le navigateur et laisse choisir au clic
les tracés à passer en magenta pur, puis enregistre en magenta ou en CutContour.

Un petit serveur HTTP local (127.0.0.1, port aléatoire, jeton secret) sert la page
et reçoit l'ordre d'enregistrement ; aucune dépendance hors bibliothèque standard.
"""

import base64
import html
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

import crunchcutcontour as conv
import eps_interpreteur as interp
import i18n
import svg_eps
from i18n import tr

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
    on ne connaît alors pas son dossier et le résultat est renvoyé en téléchargement.
    Un SVG est converti en EPS à l'ouverture (svg_eps) ; on travaille ensuite sur cet EPS."""

    def __init__(self, data, name, directory, spot_name, tolerance):
        self.name = os.path.basename(name) or "fichier.eps"
        self.directory = directory
        self.spot_name, self.tolerance = spot_name, tolerance
        self.svg = svg_eps.est_svg(data, self.name)
        self.avertissements = []
        if self.svg:
            try:
                eps, self.avertissements = svg_eps.convertir(data, self.name)
            except svg_eps.SvgError as e:
                raise ValueError(tr("“{name}”: {reason}", name=self.name, reason=e)) from None
            data = eps.encode("latin-1")
        self.dos_parts = conv.split_dos_eps(data)
        ps_bytes = self.dos_parts[0] if self.dos_parts else data
        if not ps_bytes.startswith(b"%!PS"):
            raise ValueError(tr("“{name}” is not an EPS file (it does not start with %!PS).", name=self.name))
        self.text = ps_bytes.decode("latin-1")
        self.paints, self.error = interp.interpret(self.text)
        if not self.paints:
            if self.error:
                raise ValueError(tr("No readable path in “{name}” ({error}).", name=self.name, error=self.error))
            raise ValueError(tr("No readable path in “{name}”.", name=self.name))

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
            "svg": self.svg,
            "avertissements": self.avertissements,
            "ton": self.spot_name,
            "noms": {"cutcontour": f"{base}_{self.spot_name}.eps", "magenta": f"{base}_magenta.eps",
                     "eps": f"{base}.eps"},
        }
        payload = json.dumps(donnees, ensure_ascii=False).replace("</", "<\\/")
        return fill_page(PAGE, token).replace("__DONNEES__", payload)

    def save(self, selection, mode, name):
        if mode not in ("cutcontour", "magenta", "eps") or (mode == "eps" and not self.svg):
            return {"ok": False, "message": tr("Unknown save mode.")}
        if not isinstance(name, str) or not re.fullmatch(r"[^/\\:*?\"<>|\0]+\.eps", name, re.I) \
                or name in (".eps", "..eps"):
            return {"ok": False, "message": tr("Invalid file name: use a plain name ending in .eps.")}
        out = os.path.join(self.directory, name) if self.directory else None
        if name == self.name:
            return {"ok": False, "message": tr("The output file must have a different name from the open file.")}

        chosen = {i for i in selection if isinstance(i, int) and 0 <= i < len(self.paints)
                  and self.paints[i].editable and self.paints[i].spot != self.spot_name}
        if mode == "eps":
            chosen = set()  # simple conversion du SVG : le tracé n'est pas modifié
        if mode == "magenta":
            chosen = {i for i in chosen if not self.magenta(self.paints[i])}
            if not chosen:
                return {"ok": False, "message": tr("No new path selected: nothing to save.")}
        text = apply_selection(self.text, self.paints, chosen)
        if mode == "cutcontour":
            text, count, _ = conv.convert_text(text, self.spot_name, self.tolerance)
            if count == 0:
                return {"ok": False, "message": tr("No path to convert: nothing to save.")}

        # Vérification : le fichier produit doit se relire, avec au moins autant de tracés magenta.
        check, error = interp.interpret(text)
        if error and not self.error:
            return {"ok": False, "message": tr("The output file cannot be read back ({error}): nothing was written.",
                                               error=error)}
        expected = len(chosen | {i for i, p in enumerate(self.paints) if self.magenta(p)}) if mode != "eps" else 0
        if sum(1 for p in check if self.magenta(p)) < expected:
            return {"ok": False, "message": tr("Check failed: some paths did not turn magenta. Nothing was written.")}

        data = text.encode("latin-1")
        if self.dos_parts:
            data = conv.join_dos_eps(data, *self.dos_parts[1:])
        label = {"cutcontour": self.spot_name, "magenta": tr("pure magenta"), "eps": "EPS"}[mode]
        if out is None:
            return {"ok": True, "nom": name, "donnees": base64.b64encode(data).decode("ascii"),
                    "message": tr("Downloaded ({format}): {name}", format=label, name=name)}
        existed = os.path.exists(out)
        with open(out, "wb") as fh:
            fh.write(data)
        message = (tr("Saved ({format}, existing file replaced): {path}", format=label, path=out) if existed
                   else tr("Saved ({format}): {path}", format=label, path=out))
        return {"ok": True, "chemin": out, "message": message}


MAX_UPLOAD = 200 * 1024 * 1024

# Favicon : le « n » surmonté d'une barre du logo UTBM CrunchLab, redessiné en vectoriel
# (glyphe de 181 x 281, centré dans un carré de 293). Noir, ou blanc en thème sombre.
FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-56 -6 293 293">'
               '<style>path{fill:#000}@media (prefers-color-scheme:dark){path{fill:#fff}}</style>'
               '<path d="M0 0H181V42H0Z'
               'M0 281V173.5A90.5 90.5 0 0 1 181 173.5V281H133V173.5A42.5 42.5 0 0 0 48 173.5V281Z"/></svg>')
# Même dessin en PNG 32 x 32, pour les navigateurs qui n'affichent pas les favicons SVG.
FAVICON_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAB2klEQVR42u2XOy9EQRTHf3P3rmTZiKXQS/gMFHwGjZ5EL1H4"
    "GhKFKEmEQoFaokB8A1GJWCpBITbCPq7mTHKMuc/coNiTTOZxzznzP497ZsbgJwPMA8NAJPMiZGVfgSOZJ5LdKACaIlBGa4pO"
    "XGPCBDAtoFuSB1pxDGEGj5QBgCIAhsRtAcUpULoyAYhUvwDUKIfeHd3/h5LiU0mRM0peZ3wcdcsAHKQAq+TNGZODL1BW1IEJ"
    "YFzmj8AN8KaA9MqKtwY5DWwD955i8wDsADMFDEz9jWrApmfTripWum0Bg46OQpYbYAS4UBu2xb2+1laALoGGk6y5NrcJdSIK"
    "P5SFHRXjSMYdNbe8p6KnkheEzfRVUfTpuN2On4GnmG9WZi3Db+1NuoYo13G2/TEwB4xKmwUOHZ6ejF+AsTxJacvzknK37jcS"
    "ZNcd3rb0yxkPv2+u2vck1rU6oEKVYKGsGeDKk7AHcWHw/SI96adUAbJrezIOnKTryFoE7Co9FtSkozsWgD7/6x5wtylxNMBd"
    "wtH+434QFCjRUcq3JK+SJQS/Sn0AfQB9AH8OIOlw8F04stzxIsWfWojyvoyqGQBURWbA0ZX7ZbSinue2xJ4n3PHt2hmwKFYb"
    "9Tz3voy+AHJrvSQZHKIjAAAAAElFTkSuQmCC"
)


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
        print(tr("{n} path(s) read from {name} (dropped in the browser).", n=len(ed.paints), name=ed.name))
        return {"ok": True}

    def page(self):
        return self.ed.page(self.token) if self.ed else fill_page(PAGE_DEPOT, self.token)


def _json_script(value):
    """JSON utilisable tel quel dans un <script>."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def fill_page(template, token):
    """Assemble une page : style et scripts communs, textes entre doubles crochets traduits, données."""
    page = (template.replace("__STYLE__", STYLE).replace("__DEPOT_JS__", DEPOT_JS)
            .replace("__I18N_JS__", I18N_JS))
    page = re.sub(r"\[\[(.+?)\]\]", lambda m: html.escape(tr(m.group(1))), page)
    options = "".join(f'<option value="{code}"{" selected" if code == i18n.langue() else ""}>'
                      f'{html.escape(nom)}</option>' for code, (nom, _) in i18n.LANGUES.items())
    ancien = (html.escape(tr("This browser is too old for the editor (Internet Explorer is not supported)."))
              + "<br>" + html.escape(tr("Open this address in Chrome, Firefox or Edge:")) + "<br><b>")
    favicon = (f'<link rel="icon" type="image/png" sizes="32x32" href="data:image/png;base64,{FAVICON_PNG}">\n'
               f'<link rel="icon" type="image/svg+xml" sizes="any" '
               f'href="data:image/svg+xml,{urllib.parse.quote(FAVICON_SVG)}">')
    return (page.replace("__LANGUES__", options).replace("__FAVICON__", favicon)
            .replace("__LANG__", i18n.langue())
            .replace("__ANCIEN__", json.dumps(ancien))
            .replace("__TRADUCTIONS__", _json_script(i18n.catalogue()))
            .replace("__CREDIT__", html.escape(f"{conv.COPYRIGHT} — " + tr("Author: {name}", name=conv.AUTEUR)))
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
            url = urllib.parse.urlsplit(self.path)
            if url.path == "/" + app.token:
                langue = urllib.parse.parse_qs(url.query).get("langue")
                if langue:
                    i18n.choisir(langue[0])
                self._send(200, app.page().encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._send(404, tr("Page not found").encode("utf-8"), "text/plain; charset=utf-8")

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
                self._json({"ok": False, "message": tr("File too large or invalid request.")})
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
                    result = {"ok": False, "message": tr("No file is open.")}
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
        print(tr("Internet Explorer cannot display the editor: open the address above in Chrome, Firefox or Edge."))
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
            sys.exit(tr("Error: {reason}", reason=e.strerror if isinstance(e, OSError) and e.strerror else e))
        if app.ed.error:
            print(tr("Warning: the file could only be partly read ({error}).", error=app.ed.error), file=sys.stderr)
        print(tr("{n} path(s) read from {name}.", n=len(app.ed.paints), name=app.ed.name))
    else:
        print(tr("No file given: drop an EPS file onto the page in your browser."))

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    url = f"http://127.0.0.1:{server.server_address[1]}/{app.token}"
    print(tr("Editor running at: {url}", url=url))
    print(tr("Keep this window open while you work."))
    print(tr("Press Ctrl+C or the “Quit” button to stop."))
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
.credit { color: var(--doux); font-size: 12px; white-space: nowrap; }
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
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CrunchCutContour</title>
__FAVICON__
<style>
__STYLE__
</style>
</head>
<body>
<script>
/* Écrit en ES3 : doit s'exécuter même dans un navigateur trop ancien pour l'éditeur. */
if (!window.fetch || !window.Promise || !("noModule" in document.createElement("script"))) {
  document.write('<div style="padding:16px;margin:16px;border:2px solid #b3261e;background:#fff;color:#b3261e;font:16px sans-serif">' +
    __ANCIEN__ + location.href + "</b></div>");
}
</script>
<header>
  <h1>CrunchCutContour <small id="fichier"></small></h1>
  <div class="groupe">
    <button id="moins" title="[[Zoom out]]">−</button>
    <button id="ajuster">[[Fit]]</button>
    <button id="plus" title="[[Zoom in]]">+</button>
  </div>
  <button id="aucun">[[Deselect all]]</button>
  <button id="ouvrir" title="[[Or drop an EPS or SVG file anywhere on the page]]">[[Open another file…]]</button>
  <input type="file" id="choisir" accept=".eps,.epsf,.ps,.svg,.svgz" hidden>
  <span class="espace"></span>
  <div class="groupe">
    <label><input type="radio" name="mode" value="cutcontour" checked> <span id="nom-ton"></span></label>
    <label><input type="radio" name="mode" value="magenta"> [[Pure magenta]]</label>
    <label id="mode-eps" hidden title="[[Converted SVG, without cut line]]"><input type="radio" name="mode" value="eps"> [[EPS only]]</label>
  </div>
  <div class="groupe">
    <input type="text" id="nom" spellcheck="false" aria-label="[[Output file name]]">
    <button class="principal" id="enregistrer">[[Save]]</button>
    <select id="langue" aria-label="[[Language]]">__LANGUES__</select>
    <button id="quitter">[[Quit]]</button>
  </div>
</header>
<div id="legende">
  <span class="item">
    <svg width="34" height="14"><path d="M3 7H31" stroke="#FF00FF" stroke-width="2.5"/></svg>
    [[Original cut]] <b id="n-origine">0</b>
  </span>
  <span class="item">
    <svg width="34" height="14"><path d="M3 7H31" stroke="#FF00FF" stroke-width="2.5"/>
      <path d="M3 7H31" stroke="#fff" stroke-width="1" stroke-dasharray="4 4"/></svg>
    [[Added cut]] <b id="n-ajoutee">0</b>
  </span>
  <span class="item">
    <svg width="34" height="14"><path d="M3 7H31" stroke="#7A8190" stroke-width="1.2" stroke-dasharray="1 3"/></svg>
    [[Not editable]] <b id="n-bloque">0</b>
  </span>
  <label class="item"><input type="checkbox" id="estomper"> [[Fade artwork]]</label>
</div>
<div id="alerte"></div>
<div id="notification" role="status" aria-live="polite"></div>
<div id="voile-depot">[[Drop the EPS or SVG file to open it]]</div>
<div id="zone"><div id="papier"><svg id="dessin" xmlns="http://www.w3.org/2000/svg"></svg></div></div>
<footer>
  <span id="info"></span>
  <span id="message"></span>
  <span class="credit">__CREDIT__</span>
</footer>
<script id="donnees" type="application/json">__DONNEES__</script>
<script>
"use strict";
__I18N_JS__
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
const alertes = [];
if (D.svg) {
  $("mode-eps").hidden = false;
  alertes.push(t("SVG file converted to EPS."), ...D.avertissements);
}
if (D.erreur) {
  alertes.push(t("The file could only be partly read ({error}). The paths shown can still be used.",
                 {error: D.erreur}));
}
if (D.avertissements.length || D.erreur) {
  $("alerte").style.display = "block";
  $("alerte").textContent = alertes.join(" ");
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
  const tr = D.traces[i];
  if (tr.m) { message(t("This path is already pure magenta in the file."), ""); return; }
  if (!tr.e) { message(t("This path cannot be changed on its own: it is painted by an instruction shared with other paths."), "erreur"); return; }
  if (selection.has(i)) selection.delete(i); else selection.add(i);
  dessinerEtat(i);
  majInfo();
  survoler(i);
}

let survolActuel = null;
function survoler(i) {
  if (survolActuel) { survolActuel.remove(); survolActuel = null; }
  if (i === null) { majInfo(); return; }
  const tr = D.traces[i];
  survolActuel = el("path", {d: tr.d, fill: "none", stroke: "#0091FF", "stroke-width": 2,
                             "stroke-dasharray": "5 3", "vector-effect": "non-scaling-stroke"}, gSurvol);
  const type = estTrait(i) ? t("{width} pt stroke", {width: tr.w.toLocaleString(LANGUE)}) : t("fill");
  const couleur = tr.s ? t("spot color {name}", {name: tr.s}) : tr.c;
  const etat = tr.m ? t("original cut (already in the file)") : !tr.e ? t("not editable")
             : selection.has(i) ? t("added cut — click to undo")
             : estTrait(i) ? t("click to turn it magenta") : t("click to add a magenta outline");
  $("info").textContent = t("Path #{n} — {type} — {color} — {state}", {n: i + 1, type, color: couleur, state: etat});
}

function majInfo() {
  $("n-origine").textContent = nOrigine;
  $("n-ajoutee").textContent = selection.size - nOrigine;
  $("n-bloque").textContent = nBloques;
  $("info").textContent = t("{n} paths. Click an outline to turn it pure magenta; click again to undo.",
                            {n: D.traces.length});
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

// Changement de langue : la page est rechargée ; la sélection en cours est gardée le temps du rechargement.
const CLE_ETAT = "crunchcutcontour-etat";
window.avantChangementLangue = () => {
  try {
    sessionStorage.setItem(CLE_ETAT, JSON.stringify({
      fichier: D.fichier, nb: D.traces.length, selection: [...selection], mode: modeCourant(),
      nom: $("nom").value, nomModifie, estomper: $("estomper").checked}));
  } catch (e) { /* stockage indisponible : la sélection sera perdue */ }
};
try {
  const etat = JSON.parse(sessionStorage.getItem(CLE_ETAT) || "null");
  sessionStorage.removeItem(CLE_ETAT);
  if (etat && etat.fichier === D.fichier && etat.nb === D.traces.length) {
    for (const i of etat.selection) if (D.traces[i] && D.traces[i].e) selection.add(i);
    if (etat.mode === "cutcontour" || etat.mode === "magenta" || (etat.mode === "eps" && D.svg)) {
      document.querySelector(`input[name=mode][value=${etat.mode}]`).checked = true;
    }
    $("nom").value = etat.nom;
    nomModifie = etat.nomModifie;
    if (etat.estomper) { $("estomper").checked = true; $("estomper").dispatchEvent(new Event("change")); }
    for (let i = 0; i < D.traces.length; i++) dessinerEtat(i);
    majInfo();
  }
} catch (e) { /* état illisible : on repart de zéro */ }

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
  if (erreur) notifier(t("File not opened"), texte, "erreur"); else message(texte, "");
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
  message(t("Saving…"), "");
  try {
    const res = await appeler("/api/enregistrer", {selection: [...selection], mode: modeCourant(), nom: $("nom").value.trim()});
    message(res.message, res.ok ? "ok" : "erreur");
    if (res.ok && res.donnees) {
      telecharger(res.nom, res.donnees);
      notifier(t("✓ File saved"), t("{name} — in your browser's download folder", {name: res.nom}), "ok");
    } else if (res.ok) {
      notifier(t("✓ File saved"), res.chemin, "ok");
    } else {
      notifier(t("File not saved"), res.message, "erreur");
    }
  } catch (e) {
    const texte = t("The server is not responding ({reason}).", {reason: e.message});
    message(texte, "erreur");
    notifier(t("File not saved"), texte, "erreur");
  }
};

$("quitter").onclick = async () => {
  try { await appeler("/api/quitter"); } catch (e) { /* serveur déjà arrêté */ }
  afficherArret();
};
</script>
</body>
</html>
"""


# Traduction côté navigateur, commune aux deux pages : t("English text {name}", {name: …})
# renvoie le texte dans la langue de la page (catalogue injecté par fill_page).
I18N_JS = r"""
const LANGUE = "__LANG__";
const T = __TRADUCTIONS__;
function t(texte, valeurs) {
  let r = Object.prototype.hasOwnProperty.call(T, texte) ? T[texte] : texte;
  if (valeurs) r = r.replace(/\{(\w+)\}/g, (m, k) => (k in valeurs ? String(valeurs[k]) : m));
  return r;
}
function afficherArret() {
  const p = document.createElement("p");
  p.style.padding = "24px";
  p.textContent = t("Editor stopped. You can close this tab.");
  document.body.replaceChildren(p);
}
document.getElementById("langue").addEventListener("change", e => {
  if (window.avantChangementLangue) window.avantChangementLangue();
  const url = new URL(location.href);
  url.searchParams.set("langue", e.target.value);
  location.href = url.toString();
});
"""


# Dépôt de fichier, commun à la page d'attente et à l'éditeur. La page définit JETON et
# signalerDepot(texte, erreur) ; un champ <input type=file id="choisir"> est facultatif.
DEPOT_JS = r"""
async function ouvrirFichier(fichier) {
  if (!fichier) return;
  if (!/\.(eps|epsf|ps|svg|svgz)$/i.test(fichier.name)) {
    signalerDepot(t("“{name}” is not an EPS or SVG file (.eps or .svg extension expected).", {name: fichier.name}), true);
    return;
  }
  signalerDepot(t("Reading “{name}”…", {name: fichier.name}), false);
  try {
    const r = await fetch("/api/ouvrir", {method: "POST", body: fichier,
      headers: {"X-Jeton": JETON, "X-Nom": encodeURIComponent(fichier.name)}});
    const res = await r.json();
    if (res.ok) location.reload(); else signalerDepot(res.message, true);
  } catch (e) {
    signalerDepot(t("The server is not responding ({reason}).", {reason: e.message}), true);
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
  if (fichiers && fichiers.length > 1) signalerDepot(t("One file at a time: only the first one is opened."), false);
  ouvrirFichier(fichiers && fichiers[0]);
});
const champFichier = document.getElementById("choisir");
if (champFichier) champFichier.addEventListener("change", () => ouvrirFichier(champFichier.files[0]));
"""


PAGE_DEPOT = r"""<!doctype html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CrunchCutContour</title>
__FAVICON__
<style>
__STYLE__
</style>
</head>
<body>
<script>
/* Écrit en ES3 : doit s'exécuter même dans un navigateur trop ancien pour l'éditeur. */
if (!window.fetch || !window.Promise || !("noModule" in document.createElement("script"))) {
  document.write('<div style="padding:16px;margin:16px;border:2px solid #b3261e;background:#fff;color:#b3261e;font:16px sans-serif">' +
    __ANCIEN__ + location.href + "</b></div>");
}
</script>
<header>
  <h1>CrunchCutContour</h1>
  <span class="espace"></span>
  <select id="langue" aria-label="[[Language]]">__LANGUES__</select>
  <button id="quitter">[[Quit]]</button>
</header>
<main id="depot">
  <div id="cadre-depot">
    <h2>[[Drop an EPS or SVG file here]]</h2>
    <p>[[Drag it from your file manager, or choose it.]]</p>
    <button class="principal" id="parcourir">[[Choose a file…]]</button>
    <input type="file" id="choisir" accept=".eps,.epsf,.ps,.svg,.svgz" hidden>
    <div id="etat-depot" role="status" aria-live="polite"></div>
  </div>
</main>
<footer>
  <span class="espace"></span>
  <span class="credit">__CREDIT__</span>
</footer>
<script>
"use strict";
__I18N_JS__
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
  afficherArret();
};
__DEPOT_JS__
</script>
</body>
</html>
"""
