# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
# SPDX-License-Identifier: GPL-3.0-or-later
"""Conversion SVG -> EPS (PostScript niveau 2), sans dépendance.

Gère : path (toutes les commandes, arcs compris), rect (coins arrondis), circle, ellipse,
line, polyline, polygon ; g, svg imbriqués, use et symbol, switch ; transformations ;
couleurs (nommées, #hex, rgb(), hsl(), currentColor) ; fill, stroke et leurs propriétés
(épaisseur, jointures, extrémités, pointillés) ; feuilles <style> simples (sélecteurs de
type, .classe, #id) ; viewBox, preserveAspectRatio et unités ; fichiers .svgz.
Non gérés, avec un avertissement : texte, images, dégradés et motifs (remplacés par une
couleur unie), découpes et masques, filtres, marqueurs. La transparence est approchée en
mélangeant la couleur avec du blanc (le support).

Chaque forme est écrite comme un bloc gsave … grestore distinct, avec un opérateur fill
et un opérateur stroke séparés : l'éditeur peut ainsi modifier chaque tracé seul. Une
couleur magenta pur est écrite « 1 0 1 setrgbcolor », reconnue comme ligne de découpe.
"""

import colorsys
import math
import re
import xml.etree.ElementTree as ET
import zlib

from i18n import tr

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
PX_EN_PT = 0.75                    # 1 px CSS = 0,75 pt
TAILLE_MAX = 100 * 1024 * 1024     # taille maximale d'un SVG décompressé
PROFONDEUR_MAX = 64                # imbrication maximale des use (protège des boucles)
IDENTITE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
KAPPA = 0.5522847498307936         # courbe de Bézier approchant un quart de cercle

NOMBRE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
UNITES = {"": 1.0, "px": 1.0, "pt": 4 / 3, "pc": 16.0, "mm": 96 / 25.4, "cm": 96 / 2.54,
          "in": 96.0, "q": 96 / 101.6, "em": 16.0, "rem": 16.0, "ex": 8.0}

PROPRIETES = {"fill", "fill-rule", "fill-opacity", "stroke", "stroke-width", "stroke-linejoin",
              "stroke-linecap", "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset",
              "stroke-opacity", "opacity", "display", "visibility", "color", "stop-color",
              "stop-opacity", "clip-path", "mask", "filter", "marker", "marker-start",
              "marker-mid", "marker-end"}
NON_HERITEES = {"opacity", "display", "stop-color", "stop-opacity", "clip-path", "mask", "filter"}
NON_DESSINES = {"defs", "symbol", "clipPath", "mask", "pattern", "marker", "linearGradient",
                "radialGradient", "style", "title", "desc", "metadata", "script", "filter"}

# Couleurs nommées CSS : nom puis valeur hexadécimale.
_COULEURS = """
aliceblue f0f8ff antiquewhite faebd7 aqua 00ffff aquamarine 7fffd4 azure f0ffff beige f5f5dc
bisque ffe4c4 black 000000 blanchedalmond ffebcd blue 0000ff blueviolet 8a2be2 brown a52a2a
burlywood deb887 cadetblue 5f9ea0 chartreuse 7fff00 chocolate d2691e coral ff7f50
cornflowerblue 6495ed cornsilk fff8dc crimson dc143c cyan 00ffff darkblue 00008b darkcyan 008b8b
darkgoldenrod b8860b darkgray a9a9a9 darkgreen 006400 darkgrey a9a9a9 darkkhaki bdb76b
darkmagenta 8b008b darkolivegreen 556b2f darkorange ff8c00 darkorchid 9932cc darkred 8b0000
darksalmon e9967a darkseagreen 8fbc8f darkslateblue 483d8b darkslategray 2f4f4f
darkslategrey 2f4f4f darkturquoise 00ced1 darkviolet 9400d3 deeppink ff1493 deepskyblue 00bfff
dimgray 696969 dimgrey 696969 dodgerblue 1e90ff firebrick b22222 floralwhite fffaf0
forestgreen 228b22 fuchsia ff00ff gainsboro dcdcdc ghostwhite f8f8ff gold ffd700
goldenrod daa520 gray 808080 grey 808080 green 008000 greenyellow adff2f honeydew f0fff0
hotpink ff69b4 indianred cd5c5c indigo 4b0082 ivory fffff0 khaki f0e68c lavender e6e6fa
lavenderblush fff0f5 lawngreen 7cfc00 lemonchiffon fffacd lightblue add8e6 lightcoral f08080
lightcyan e0ffff lightgoldenrodyellow fafad2 lightgray d3d3d3 lightgreen 90ee90 lightgrey d3d3d3
lightpink ffb6c1 lightsalmon ffa07a lightseagreen 20b2aa lightskyblue 87cefa
lightslategray 778899 lightslategrey 778899 lightsteelblue b0c4de lightyellow ffffe0
lime 00ff00 limegreen 32cd32 linen faf0e6 magenta ff00ff maroon 800000
mediumaquamarine 66cdaa mediumblue 0000cd mediumorchid ba55d3 mediumpurple 9370db
mediumseagreen 3cb371 mediumslateblue 7b68ee mediumspringgreen 00fa9a mediumturquoise 48d1cc
mediumvioletred c71585 midnightblue 191970 mintcream f5fffa mistyrose ffe4e1 moccasin ffe4b5
navajowhite ffdead navy 000080 oldlace fdf5e6 olive 808000 olivedrab 6b8e23 orange ffa500
orangered ff4500 orchid da70d6 palegoldenrod eee8aa palegreen 98fb98 paleturquoise afeeee
palevioletred db7093 papayawhip ffefd5 peachpuff ffdab9 peru cd853f pink ffc0cb plum dda0dd
powderblue b0e0e6 purple 800080 rebeccapurple 663399 red ff0000 rosybrown bc8f8f
royalblue 4169e1 saddlebrown 8b4513 salmon fa8072 sandybrown f4a460 seagreen 2e8b57
seashell fff5ee sienna a0522d silver c0c0c0 skyblue 87ceeb slateblue 6a5acd slategray 708090
slategrey 708090 snow fffafa springgreen 00ff7f steelblue 4682b4 tan d2b48c teal 008080
thistle d8bfd8 tomato ff6347 turquoise 40e0d0 violet ee82ee wheat f5deb3 white ffffff
whitesmoke f5f5f5 yellow ffff00 yellowgreen 9acd32
""".split()
COULEURS_NOMMEES = dict(zip(_COULEURS[::2], _COULEURS[1::2]))


class SvgError(Exception):
    pass


def est_svg(data, nom=""):
    """Vrai si les données (ou le nom de fichier) désignent un SVG ou un SVGZ."""
    if nom.lower().endswith((".svg", ".svgz")):
        return True
    if data[:2] == b"\x1f\x8b":
        return True
    debut = data[:4096].lstrip()
    return debut.startswith(b"<") and b"<svg" in debut


# --- Lecture du fichier ---------------------------------------------------------

def _charger(data):
    if data[:2] == b"\x1f\x8b":  # SVGZ
        d = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            data = d.decompress(data, TAILLE_MAX)
        except zlib.error as e:
            raise SvgError(tr("Invalid SVGZ file ({reason}).", reason=e)) from None
        if d.unconsumed_tail:
            raise SvgError(tr("SVG file too large."))
    if b"<!ENTITY" in data:
        # Refusé : les entités XML permettent des expansions démesurées (« billion laughs »).
        raise SvgError(tr("SVG files that declare XML entities are not supported."))
    try:
        racine = ET.fromstring(data)
    except ET.ParseError as e:
        raise SvgError(tr("Invalid SVG file ({reason}).", reason=e)) from None
    if _local(racine.tag) != "svg":
        raise SvgError(tr("This is not an SVG file (root element: {tag}).", tag=_local(racine.tag)))
    return racine


def _local(tag):
    """Nom d'un élément SVG sans espace de noms, ou None pour un autre espace de noms."""
    if not isinstance(tag, str):
        return None
    if tag.startswith("{"):
        ns, _, nom = tag[1:].partition("}")
        return nom if ns == SVG_NS else None
    return tag


# --- Nombres, longueurs, transformations ----------------------------------------

def _nombres(texte):
    return [float(n) for n in NOMBRE.findall(texte or "")]


def _longueur(valeur, reference=0.0, defaut=0.0):
    """Longueur SVG en px ; les pourcentages se rapportent à `reference`."""
    if valeur is None:
        return defaut
    m = re.match(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)", str(valeur))
    if not m:
        return defaut
    nombre, unite = float(m.group(1)), m.group(2).lower()
    if unite == "%":
        return nombre * reference / 100
    return nombre * UNITES.get(unite, 1.0)


def _mul(m, n):
    """m puis n (convention PostScript et SVG : x' = a x + c y + e)."""
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def _transformation(texte):
    m = IDENTITE
    for nom, args in re.findall(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)", texte or ""):
        v = _nombres(args)
        t = IDENTITE
        if nom == "matrix" and len(v) == 6:
            t = tuple(v)
        elif nom == "translate" and v:
            t = (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0)
        elif nom == "scale" and v:
            t = (v[0], 0.0, 0.0, v[1] if len(v) > 1 else v[0], 0.0, 0.0)
        elif nom == "rotate" and v:
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0.0, 0.0)
            if len(v) == 3:
                t = _mul(_mul((1.0, 0.0, 0.0, 1.0, -v[1], -v[2]), t), (1.0, 0.0, 0.0, 1.0, v[1], v[2]))
        elif nom == "skewX" and v:
            t = (1.0, 0.0, math.tan(math.radians(v[0])), 1.0, 0.0, 0.0)
        elif nom == "skewY" and v:
            t = (1.0, math.tan(math.radians(v[0])), 0.0, 1.0, 0.0, 0.0)
        # Dans l'attribut, la transformation la plus à droite s'applique en premier.
        m = _mul(t, m)
    return m


def _viewbox(viewbox, largeur, hauteur, aspect):
    """Matrice qui place la viewBox dans un cadre largeur x hauteur (preserveAspectRatio)."""
    v = _nombres(viewbox)
    if len(v) != 4 or v[2] <= 0 or v[3] <= 0:
        return IDENTITE
    vx, vy, vw, vh = v
    sx, sy = largeur / vw, hauteur / vh
    mots = (aspect or "xMidYMid meet").split()
    alignement = mots[0] if mots else "xMidYMid"
    if alignement != "none":
        s = max(sx, sy) if "slice" in mots else min(sx, sy)
        sx = sy = s
    tx, ty = -vx * sx, -vy * sy
    if alignement != "none":
        if "xMid" in alignement:
            tx += (largeur - vw * sx) / 2
        elif "xMax" in alignement:
            tx += largeur - vw * sx
        if "YMid" in alignement:
            ty += (hauteur - vh * sy) / 2
        elif "YMax" in alignement:
            ty += hauteur - vh * sy
    return (sx, 0.0, 0.0, sy, tx, ty)


# --- Tracés ------------------------------------------------------------------------

def _jetons_chemin(d):
    """Commandes et nombres de l'attribut d, avec lecture des drapeaux d'arc (0/1 collés)."""
    i, n = 0, len(d)
    jetons = []
    while i < n:
        c = d[i]
        if c in " \t\r\n,":
            i += 1
        elif c.isalpha():
            jetons.append(c)
            i += 1
        else:
            m = NOMBRE.match(d, i)
            if not m:
                break  # donnée invalide : on garde ce qui précède, comme les navigateurs
            jetons.append(m.group(0))
            i = m.end()
    return jetons


def _chemin(d):
    """Segments absolus (M, L, C, Z) d'un attribut d."""
    jetons = _jetons_chemin(d)
    segments = []
    x = y = sx = sy = 0.0
    dernier_ctrl = None   # dernier point de contrôle (pour S et T) et type de la commande précédente
    i, commande = 0, None

    def nombre():
        nonlocal i
        v = float(jetons[i])
        i += 1
        return v

    def drapeau():
        # Un drapeau d'arc peut être collé au nombre suivant (« 01 » = 0 puis 1).
        nonlocal i
        t = jetons[i]
        if t[0] in "01":
            if len(t) > 1:
                jetons[i] = t[1:]
            else:
                i += 1
            return t[0] == "1"
        raise ValueError(t)

    try:
        while i < len(jetons):
            if jetons[i].isalpha():
                commande = jetons[i]
                i += 1
                if commande in "Zz":
                    if segments:
                        segments.append(("Z",))
                    x, y = sx, sy
                    dernier_ctrl = None
                    continue
            elif commande is None:
                break
            rel = commande.islower()
            c = commande.upper()
            ox, oy = (x, y) if rel else (0.0, 0.0)
            if c == "M":
                x, y = ox + nombre(), oy + nombre()
                segments.append(("M", x, y))
                sx, sy = x, y
                commande = "l" if rel else "L"   # les paires suivantes sont des lignes
                dernier_ctrl = None
            elif c == "L":
                x, y = ox + nombre(), oy + nombre()
                segments.append(("L", x, y))
                dernier_ctrl = None
            elif c == "H":
                x = ox + nombre()
                segments.append(("L", x, y))
                dernier_ctrl = None
            elif c == "V":
                y = oy + nombre()
                segments.append(("L", x, y))
                dernier_ctrl = None
            elif c in "CS":
                if c == "C":
                    x1, y1 = ox + nombre(), oy + nombre()
                else:
                    x1, y1 = (2 * x - dernier_ctrl[1], 2 * y - dernier_ctrl[2]) \
                        if dernier_ctrl and dernier_ctrl[0] == "C" else (x, y)
                x2, y2 = ox + nombre(), oy + nombre()
                x, y = ox + nombre(), oy + nombre()
                segments.append(("C", x1, y1, x2, y2, x, y))
                dernier_ctrl = ("C", x2, y2)
            elif c in "QT":
                if c == "Q":
                    qx, qy = ox + nombre(), oy + nombre()
                else:
                    qx, qy = (2 * x - dernier_ctrl[1], 2 * y - dernier_ctrl[2]) \
                        if dernier_ctrl and dernier_ctrl[0] == "Q" else (x, y)
                nx, ny = ox + nombre(), oy + nombre()
                segments.append(("C", x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y),
                                 nx + 2 / 3 * (qx - nx), ny + 2 / 3 * (qy - ny), nx, ny))
                x, y = nx, ny
                dernier_ctrl = ("Q", qx, qy)
            elif c == "A":
                rx, ry, phi = nombre(), nombre(), nombre()
                grand, sens = drapeau(), drapeau()
                nx, ny = ox + nombre(), oy + nombre()
                segments += _arc(x, y, rx, ry, phi, grand, sens, nx, ny)
                x, y = nx, ny
                dernier_ctrl = None
            else:
                break
            if segments and segments[0][0] != "M":
                segments.insert(0, ("M", 0.0, 0.0))
    except (IndexError, ValueError):
        pass  # fin de données invalide : on garde les segments déjà lus
    return segments


def _arc(x1, y1, rx, ry, phi, grand, sens, x2, y2):
    """Arc elliptique SVG converti en courbes de Bézier (spécification SVG, annexe F.6)."""
    if (x1, y1) == (x2, y2):
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return [("L", x2, y2)]
    cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if grand == sens:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x1 + x2) / 2, sp * cxp + cp * cyp + (y1 + y2) / 2

    def angle(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    debut, ecart = angle(1, 0, ux, uy), angle(ux, uy, vx, vy)
    if not sens and ecart > 0:
        ecart -= 2 * math.pi
    elif sens and ecart < 0:
        ecart += 2 * math.pi
    n = max(1, math.ceil(abs(ecart) / (math.pi / 2) - 1e-9))
    pas = ecart / n
    k = 4 / 3 * math.tan(pas / 4)

    def point(u, v):
        return cx + rx * u * cp - ry * v * sp, cy + rx * u * sp + ry * v * cp

    segments = []
    for j in range(n):
        a1 = debut + j * pas
        a2 = a1 + pas
        p1 = point(math.cos(a1) - k * math.sin(a1), math.sin(a1) + k * math.cos(a1))
        p2 = point(math.cos(a2) + k * math.sin(a2), math.sin(a2) - k * math.cos(a2))
        p3 = (x2, y2) if j == n - 1 else point(math.cos(a2), math.sin(a2))
        segments.append(("C",) + p1 + p2 + p3)
    return segments


def _ellipse(cx, cy, rx, ry):
    kx, ky = rx * KAPPA, ry * KAPPA
    return [("M", cx + rx, cy),
            ("C", cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry),
            ("C", cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy),
            ("C", cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry),
            ("C", cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy),
            ("Z",)]


def _rectangle(x, y, w, h, rx, ry):
    if rx <= 0 or ry <= 0:
        return [("M", x, y), ("L", x + w, y), ("L", x + w, y + h), ("L", x, y + h), ("Z",)]
    rx, ry = min(rx, w / 2), min(ry, h / 2)
    kx, ky = rx * (1 - KAPPA), ry * (1 - KAPPA)
    return [("M", x + rx, y), ("L", x + w - rx, y),
            ("C", x + w - kx, y, x + w, y + ky, x + w, y + ry), ("L", x + w, y + h - ry),
            ("C", x + w, y + h - ky, x + w - kx, y + h, x + w - rx, y + h), ("L", x + rx, y + h),
            ("C", x + kx, y + h, x, y + h - ky, x, y + h - ry), ("L", x, y + ry),
            ("C", x, y + ky, x + kx, y, x + rx, y), ("Z",)]


# --- Styles ------------------------------------------------------------------------

def _declarations(texte):
    styles = {}
    for decl in (texte or "").split(";"):
        nom, _, valeur = decl.partition(":")
        nom, valeur = nom.strip().lower(), valeur.replace("!important", "").strip()
        if nom and valeur:
            styles[nom] = valeur
    return styles


def _feuilles_de_style(racine):
    """Règles des éléments <style> : [(spécificité, ordre, (type, ids, classes), déclarations)]."""
    regles = []
    for el in racine.iter():
        if _local(el.tag) != "style" or not el.text:
            continue
        css = re.sub(r"/\*.*?\*/", "", el.text, flags=re.S)
        css = re.sub(r"@[^{;]*;", "", css)
        for selecteurs, corps in re.findall(r"([^{}@]+)\{([^{}]*)\}", css):
            decl = _declarations(corps)
            for sel in selecteurs.split(","):
                m = re.fullmatch(r"\s*(\*|[A-Za-z][\w-]*)?((?:[.#][\w-]+)*)\s*", sel)
                if not m or not (m.group(1) or m.group(2)):
                    continue  # sélecteur complexe (descendant, attribut…) : ignoré
                type_ = m.group(1) if m.group(1) not in (None, "*") else None
                ids = re.findall(r"#([\w-]+)", m.group(2))
                classes = re.findall(r"\.([\w-]+)", m.group(2))
                regles.append(((len(ids), len(classes), 1 if type_ else 0), len(regles),
                               (type_, ids, classes), decl))
    regles.sort(key=lambda r: (r[0], r[1]))
    return regles


def _parse_couleur(valeur, style):
    """(r, g, b) entre 0 et 1, None pour none, ou ("url", id, repli)."""
    v = (valeur or "").strip()
    bas = v.lower()
    if not v or bas in ("none", "transparent"):
        return None
    if bas.startswith("url("):
        m = re.match(r"url\(\s*['\"]?#?([^)'\"]*)['\"]?\s*\)\s*(.*)", v, re.I)
        if m:
            return ("url", m.group(1), _parse_couleur(m.group(2), style) if m.group(2) else None)
        return None
    if bas == "currentcolor":
        return _parse_couleur(style.get("color", "black"), {})
    if bas in COULEURS_NOMMEES:
        bas = "#" + COULEURS_NOMMEES[bas]
    if bas.startswith("#"):
        h = bas[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h[:3])
        if len(h) in (6, 8) and re.fullmatch(r"[0-9a-f]+", h):
            return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return (0.0, 0.0, 0.0)
    m = re.match(r"(rgba?|hsla?)\(([^)]*)\)", bas)
    if m:
        parties = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
        if len(parties) < 3:
            return (0.0, 0.0, 0.0)

        def composante(p, echelle):
            n = float(NOMBRE.match(p).group(0)) if NOMBRE.match(p) else 0.0
            return n / 100 if p.endswith("%") else n / echelle

        if m.group(1).startswith("rgb"):
            return tuple(max(0.0, min(1.0, composante(p, 255))) for p in parties[:3])
        teinte = (float(NOMBRE.match(parties[0]).group(0)) if NOMBRE.match(parties[0]) else 0.0) / 360 % 1
        r, g, b = colorsys.hls_to_rgb(teinte, composante(parties[2], 100), composante(parties[1], 100))
        return (r, g, b)
    return (0.0, 0.0, 0.0)  # couleur inconnue : noir, comme le ferait la plupart des logiciels


def _opacite(valeur):
    """Opacité entre 0 et 1 (nombre ou pourcentage) ; 1 par défaut."""
    try:
        v = (valeur or "1").strip()
        v = float(v[:-1]) / 100 if v.endswith("%") else float(v)
    except ValueError:
        return 1.0
    return max(0.0, min(1.0, v))


def _sur_blanc(couleur, opacite):
    """Couleur vue sur un support blanc : approximation de la transparence, que l'EPS n'a pas."""
    if opacite >= 1:
        return couleur
    return tuple(c * opacite + (1 - opacite) for c in couleur)


# --- Conversion ----------------------------------------------------------------------

def _fmt(v):
    if abs(v) < 5e-7:
        return "0"
    return f"{v:.4f}".rstrip("0").rstrip(".")


class _Convertisseur:
    def __init__(self, racine):
        self.racine = racine
        self.regles = _feuilles_de_style(racine)
        self.par_id = {el.get("id"): el for el in racine.iter() if el.get("id")}
        self.lignes = []
        self.avertissements = set()

    def avertir(self, code):
        self.avertissements.add(code)

    # Styles
    def style(self, el, parent):
        nom = _local(el.tag)
        s = {k: v for k, v in parent.items() if k not in NON_HERITEES}
        for k in PROPRIETES:
            if el.get(k) is not None:
                s[k] = el.get(k).strip()
        classes = (el.get("class") or "").split()
        ident = el.get("id")
        for _, _, (type_, ids, cls), decl in self.regles:
            if (type_ is None or type_ == nom) and all(i == ident for i in ids) \
                    and all(c in classes for c in cls):
                s.update(decl)
        s.update(_declarations(el.get("style")))
        for k, v in list(s.items()):
            if v == "inherit":
                if k in parent:
                    s[k] = parent[k]
                else:
                    del s[k]
        return s

    def peinture(self, valeur, style):
        couleur = _parse_couleur(valeur, style)
        if isinstance(couleur, tuple) and couleur and couleur[0] == "url":
            _, ident, repli = couleur
            cible = self.par_id.get(ident)
            if cible is not None and _local(cible.tag) in ("linearGradient", "radialGradient"):
                self.avertir("degrade")
                moyenne = self.couleur_degrade(cible, style)
                return moyenne if moyenne is not None else repli
            self.avertir("degrade")
            return repli if repli is not None else (0.5, 0.5, 0.5)
        return couleur

    def couleur_degrade(self, degrade, style, profondeur=0):
        """Moyenne des couleurs des arrêts d'un dégradé (en suivant href), mélangées avec le
        blanc selon leur opacité : une ombre noire presque transparente donne un gris clair."""
        arrets = [e for e in degrade if _local(e.tag) == "stop"]
        if not arrets and profondeur < 8:
            ref = (degrade.get("href") or degrade.get(XLINK_HREF) or "").lstrip("#")
            if ref in self.par_id:
                return self.couleur_degrade(self.par_id[ref], style, profondeur + 1)
        couleurs = []
        for arret in arrets:
            s = self.style(arret, {})
            c = _parse_couleur(s.get("stop-color", "black"), style)
            if isinstance(c, tuple) and c and c[0] != "url":
                couleurs.append(_sur_blanc(c, _opacite(s.get("stop-opacity"))))
        if not couleurs:
            return None
        return tuple(sum(c[i] for c in couleurs) / len(couleurs) for i in range(3))

    # Parcours
    def element(self, el, ctm, parent, cadre, profondeur=0):
        nom = _local(el.tag)
        if nom is None or nom in NON_DESSINES:
            return
        s = self.style(el, parent)
        if s.get("display") == "none":
            return
        for k, code in (("clip-path", "decoupe"), ("mask", "decoupe"), ("filter", "filtre")):
            if s.get(k, "none") != "none":
                self.avertir(code)
        if any(s.get(k, "none") != "none" for k in ("marker", "marker-start", "marker-mid", "marker-end")):
            self.avertir("marqueur")
        ctm = _mul(_transformation(el.get("transform")), ctm)

        if nom in ("g", "a"):
            for enfant in el:
                self.element(enfant, ctm, s, cadre, profondeur)
        elif nom == "switch":
            for enfant in el:
                if _local(enfant.tag) not in (None, "foreignObject") and enfant.get("display") != "none":
                    self.element(enfant, ctm, s, cadre, profondeur)
                    break
        elif nom == "svg":
            x, y = _longueur(el.get("x"), cadre[0]), _longueur(el.get("y"), cadre[1])
            w = _longueur(el.get("width"), cadre[0], cadre[0])
            h = _longueur(el.get("height"), cadre[1], cadre[1])
            vb = _viewbox(el.get("viewBox"), w, h, el.get("preserveAspectRatio"))
            ctm = _mul(_mul(vb, (1.0, 0.0, 0.0, 1.0, x, y)), ctm)
            for enfant in el:
                self.element(enfant, ctm, s, (w, h), profondeur)
        elif nom == "use":
            ref = (el.get("href") or el.get(XLINK_HREF) or "").lstrip("#")
            cible = self.par_id.get(ref)
            if cible is None or profondeur >= PROFONDEUR_MAX:
                return
            x, y = _longueur(el.get("x"), cadre[0]), _longueur(el.get("y"), cadre[1])
            ctm = _mul((1.0, 0.0, 0.0, 1.0, x, y), ctm)
            if _local(cible.tag) == "symbol":
                st = self.style(cible, s)
                w = _longueur(el.get("width"), cadre[0], cadre[0])
                h = _longueur(el.get("height"), cadre[1], cadre[1])
                vb = _viewbox(cible.get("viewBox"), w, h, cible.get("preserveAspectRatio"))
                ctm = _mul(vb, ctm)
                for enfant in cible:
                    self.element(enfant, ctm, st, (w, h), profondeur + 1)
            else:
                self.element(cible, ctm, s, cadre, profondeur + 1)
        elif nom in ("text", "tspan", "textPath"):
            self.avertir("texte")
        elif nom == "image":
            self.avertir("image")
        elif nom == "foreignObject":
            self.avertir("texte")
        else:
            segments = self.forme(el, nom, cadre)
            if segments:
                self.dessiner(segments, ctm, s, ferme=nom != "line")

    def forme(self, el, nom, cadre):
        w0, h0 = cadre
        diag = math.hypot(w0, h0) / math.sqrt(2)
        L = _longueur
        if nom == "path":
            return _chemin(el.get("d") or "")
        if nom == "rect":
            x, y = L(el.get("x"), w0), L(el.get("y"), h0)
            w, h = L(el.get("width"), w0), L(el.get("height"), h0)
            if w <= 0 or h <= 0:
                return []
            rx, ry = el.get("rx"), el.get("ry")
            rx = L(rx, w0) if rx not in (None, "auto") else None
            ry = L(ry, h0) if ry not in (None, "auto") else None
            rx, ry = (rx if rx is not None else ry or 0.0), (ry if ry is not None else rx or 0.0)
            return _rectangle(x, y, w, h, rx, ry)
        if nom == "circle":
            r = L(el.get("r"), diag)
            return _ellipse(L(el.get("cx"), w0), L(el.get("cy"), h0), r, r) if r > 0 else []
        if nom == "ellipse":
            rx, ry = el.get("rx"), el.get("ry")
            rx = L(rx, w0) if rx not in (None, "auto") else None
            ry = L(ry, h0) if ry not in (None, "auto") else None
            rx, ry = (rx if rx is not None else ry or 0.0), (ry if ry is not None else rx or 0.0)
            return _ellipse(L(el.get("cx"), w0), L(el.get("cy"), h0), rx, ry) if rx > 0 and ry > 0 else []
        if nom == "line":
            return [("M", L(el.get("x1"), w0), L(el.get("y1"), h0)),
                    ("L", L(el.get("x2"), w0), L(el.get("y2"), h0))]
        if nom in ("polyline", "polygon"):
            v = _nombres(el.get("points"))
            pts = list(zip(v[0::2], v[1::2]))
            if len(pts) < 2:
                return []
            segments = [("M",) + pts[0]] + [("L",) + p for p in pts[1:]]
            return segments + [("Z",)] if nom == "polygon" else segments
        return []

    def dessiner(self, segments, ctm, s, ferme):
        if s.get("visibility") in ("hidden", "collapse"):
            return

        def opacite(cle):
            return _opacite(s.get(cle))

        opacite_globale = opacite("opacity")
        remplissage = self.peinture(s.get("fill", "black"), s) if ferme else None
        trait = self.peinture(s.get("stroke", "none"), s)
        if remplissage is not None and (opacite("fill-opacity") <= 0 or opacite_globale <= 0):
            remplissage = None
        if trait is not None and (opacite("stroke-opacity") <= 0 or opacite_globale <= 0):
            trait = None
        epaisseur = _longueur(s.get("stroke-width", "1"), 1.0, 1.0)
        if epaisseur <= 0:
            trait = None
        if remplissage is None and trait is None:
            return
        if min(opacite("fill-opacity") if remplissage else 1, opacite("stroke-opacity") if trait else 1,
               opacite_globale) < 1:
            self.avertir("transparence")
        if remplissage is not None:
            remplissage = _sur_blanc(remplissage, opacite("fill-opacity") * opacite_globale)
        if trait is not None:
            trait = _sur_blanc(trait, opacite("stroke-opacity") * opacite_globale)
        if abs(ctm[0] * ctm[3] - ctm[1] * ctm[2]) < 1e-12:
            return  # transformation dégénérée : rien de visible

        out = self.lignes
        out.append("gsave")
        out.append("[" + " ".join(_fmt(v) for v in ctm) + "] concat")
        out.append("newpath")
        out.extend(self.operateurs(segments))
        if remplissage is not None:
            op = "eofill" if s.get("fill-rule") == "evenodd" else "fill"
            out.append(" ".join(_fmt(c) for c in remplissage) + " setrgbcolor")
            out.append(f"gsave {op} grestore" if trait is not None else op)
        if trait is not None:
            jointure = {"miter": 0, "round": 1, "bevel": 2}.get(s.get("stroke-linejoin"), 0)
            extremite = {"butt": 0, "round": 1, "square": 2}.get(s.get("stroke-linecap"), 0)
            try:
                onglet = max(1.0, float(s.get("stroke-miterlimit", "4")))
            except ValueError:
                onglet = 4.0
            out.append(" ".join(_fmt(c) for c in trait) + " setrgbcolor")
            out.append(f"{_fmt(epaisseur)} setlinewidth {jointure} setlinejoin {extremite} setlinecap "
                       f"{_fmt(onglet)} setmiterlimit")
            tirets = [_longueur(t, 1.0) for t in re.split(r"[\s,]+", s.get("stroke-dasharray", "none").strip())
                      if t and t != "none"]
            if tirets and any(t > 0 for t in tirets) and all(t >= 0 for t in tirets):
                if len(tirets) % 2:
                    tirets *= 2
                decalage = _longueur(s.get("stroke-dashoffset", "0"), 1.0)
                out.append("[" + " ".join(_fmt(t) for t in tirets) + f"] {_fmt(decalage)} setdash")
            out.append("stroke")
        out.append("grestore")

    @staticmethod
    def operateurs(segments):
        lignes, courante = [], []
        for seg in segments:
            if seg[0] == "M":
                courante.append(f"{_fmt(seg[1])} {_fmt(seg[2])} moveto")
            elif seg[0] == "L":
                courante.append(f"{_fmt(seg[1])} {_fmt(seg[2])} lineto")
            elif seg[0] == "C":
                courante.append(" ".join(_fmt(v) for v in seg[1:]) + " curveto")
            else:
                courante.append("closepath")
            if sum(len(c) + 1 for c in courante) > 90:
                lignes.append(" ".join(courante))
                courante = []
        if courante:
            lignes.append(" ".join(courante))
        return lignes


MESSAGES = {
    "texte": lambda: tr("Text is not converted: turn it into paths (outlines) before exporting the SVG."),
    "image": lambda: tr("Embedded images are not converted."),
    "degrade": lambda: tr("Gradients and patterns are replaced by a flat color."),
    "decoupe": lambda: tr("Clipping paths and masks are ignored."),
    "filtre": lambda: tr("Filters (blur, shadow…) are ignored."),
    "marqueur": lambda: tr("Markers (arrowheads…) are ignored."),
    "transparence": lambda: tr("Transparency is approximated: semi-transparent colors are blended with white."),
}


def convertir(data, titre="svg"):
    """Convertit un SVG (octets) en EPS : renvoie (texte EPS ASCII, [avertissements])."""
    racine = _charger(data)
    # Taille de la page : width/height du SVG racine, sinon sa viewBox, sinon 300 x 150 px.
    vb = _nombres(racine.get("viewBox"))
    vb_ok = len(vb) == 4 and vb[2] > 0 and vb[3] > 0

    def dimension(attr, index, defaut):
        valeur = racine.get(attr)
        if valeur is None or valeur.strip().endswith("%") or valeur.strip() == "auto":
            return vb[index] if vb_ok else defaut
        return _longueur(valeur, 0.0, defaut)

    largeur, hauteur = dimension("width", 2, 300.0), dimension("height", 3, 150.0)
    if largeur <= 0 or hauteur <= 0:
        raise SvgError(tr("The SVG has no usable size (width/height)."))
    w_pt, h_pt = largeur * PX_EN_PT, hauteur * PX_EN_PT
    # px SVG (y vers le bas) -> points PostScript (y vers le haut)
    page = (PX_EN_PT, 0.0, 0.0, -PX_EN_PT, 0.0, h_pt)
    ctm = _mul(_viewbox(racine.get("viewBox"), largeur, hauteur, racine.get("preserveAspectRatio")), page)

    conv = _Convertisseur(racine)
    style_racine = conv.style(racine, {})
    for enfant in racine:
        conv.element(enfant, ctm, style_racine, (vb[2], vb[3]) if vb_ok else (largeur, hauteur))
    if not conv.lignes:
        conv.avertir("vide")

    titre_ascii = titre.encode("ascii", "replace").decode("ascii").replace("(", "[").replace(")", "]")
    entete = [
        "%!PS-Adobe-3.0 EPSF-3.0",
        "%%Creator: CrunchCutContour (SVG)",
        f"%%Title: ({titre_ascii})",
        f"%%BoundingBox: 0 0 {math.ceil(w_pt - 1e-6)} {math.ceil(h_pt - 1e-6)}",
        f"%%HiResBoundingBox: 0 0 {_fmt(w_pt)} {_fmt(h_pt)}",
        "%%LanguageLevel: 2",
        "%%Pages: 1",
        "%%EndComments",
        "%%Page: 1 1",
        "gsave",
        f"0 0 {_fmt(w_pt)} {_fmt(h_pt)} rectclip",
    ]
    fin = ["grestore", "showpage", "%%EOF", ""]
    avertissements = [MESSAGES[c]() for c in MESSAGES if c in conv.avertissements]
    if "vide" in conv.avertissements:
        avertissements.append(tr("The SVG contains no shape that can be converted."))
    return "\n".join(entete + conv.lignes + fin), avertissements
