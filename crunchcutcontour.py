#!/usr/bin/env python3
# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
"""Convertit les couleurs magenta pur d'un fichier EPS en ton direct CutContour.

Par défaut, le fichier s'ouvre dans un éditeur (navigateur) où l'on clique sur
les contours à passer en magenta pur avant d'enregistrer (voir eps_editeur.py).
Avec --auto, la conversion se fait directement, sans éditeur. Un fichier SVG est d'abord
converti en EPS (svg_eps.py) ; --to-eps fait seulement cette conversion.

Le script repère dans le code PostScript chaque réglage de couleur magenta pur :
  - RVB  : 1 0 1 setrgbcolor   (ou un alias, ex. « 1 0 1 rg » dans les EPS cairo)
  - CMJN : 0 1 0 0 setcmykcolor (ou un alias)
et le remplace par un ton direct (espace Separation) nommé CutContour, rendu en
magenta pur (C0 M100 J0 N0), reconnu par les RIP d'impression-découpe
(VersaWorks, Onyx, Caldera...). Les commentaires DSC de l'en-tête sont mis à jour.

Usage :
  python3 crunchcutcontour.py [entree.eps]                     (éditeur ; sans fichier,
                                                              déposez-le dans la page)
  python3 crunchcutcontour.py --auto entree.eps [-o sortie.eps]
  python3 crunchcutcontour.py --to-eps entree.svg [-o sortie.eps]
  Option --language en|fr (ou --langue) : langue de l'interface (voir i18n.py).
"""

import argparse
import os
import re
import struct
import sys

import i18n
import svg_eps
from i18n import tr

VERSION = "1.0.0"
COPYRIGHT = "Copyright © 2026 UTBM CrunchLab"
AUTEUR = "Alexandre Willaume"

MAGENTA_RVB = (1.0, 0.0, 1.0)
MAGENTA_CMJN = (0.0, 1.0, 0.0, 0.0)

WHITESPACE = "\0\t\n\f\r "
DELIMITERS = "()<>[]{}/%"
NUMBER_RE = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")

DOS_EPS_MAGIC = b"\xc5\xd0\xd3\xc6"


def spot_color_code(name):
    """Code PostScript qui active le ton direct `name` à 100 %, simulé en magenta."""
    return f"[/Separation /{name} /DeviceCMYK {{0 exch 0 0}}] setcolorspace 1 setcolor"


def find_aliases(text, operator):
    """Noms de procédures définies comme simple alias de `operator` (ex. /rg)."""
    name = r"/([^\s/{}\[\]()<>%]+)\s*"
    patterns = [
        name + r"\{\s*" + operator + r"\s*\}\s*(?:bind\s+)?def",
        name + r"/" + operator + r"\s+load\s+def",
    ]
    aliases = set()
    for pattern in patterns:
        aliases.update(re.findall(pattern, text))
    return aliases


def tokenize(text):
    """Produit (début, fin, texte) pour chaque objet PostScript.

    Les commentaires, chaînes et blocs de données DSC sont sautés : ils ne
    produisent qu'un jeton neutre, pour ne jamais être modifiés.
    """
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in WHITESPACE:
            i += 1
        elif ch == "%":
            end = text.find("\n", i)
            end = n if end == -1 else end + 1
            at_line_start = i == 0 or text[i - 1] in "\r\n"
            comment = text[i:end]
            i = skip_dsc_data(text, end, comment) if at_line_start else end
        elif ch == "(":
            start, depth, i = i, 1, i + 1
            while i < n and depth:
                c = text[i]
                if c == "\\":
                    i += 1
                elif c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                i += 1
            yield start, i, "(string)"
        elif text.startswith("<~", i):
            end = text.find("~>", i + 2)
            start, i = i, n if end == -1 else end + 2
            yield start, i, "(string)"
        elif text.startswith("<<", i) or text.startswith(">>", i):
            yield i, i + 2, text[i:i + 2]
            i += 2
        elif ch == "<":
            end = text.find(">", i + 1)
            start, i = i, n if end == -1 else end + 1
            yield start, i, "(string)"
        elif ch in "[]{})>":
            yield i, i + 1, ch
            i += 1
        else:
            start = i
            i += 1  # le « / » initial d'un nom, ou le premier caractère
            if ch == "/" and i < n and text[i] == "/":
                i += 1
            while i < n and text[i] not in WHITESPACE and text[i] not in DELIMITERS:
                i += 1
            yield start, i, text[start:i]


def skip_dsc_data(text, pos, comment):
    """Saute le contenu d'un bloc %%BeginData / %%BeginBinary (données brutes)."""
    m = re.match(r"%%BeginBinary:\s*(\d+)", comment)
    if m:
        return pos + int(m.group(1))
    m = re.match(r"%%BeginData:\s*(\d+)(?:\s+\w+)?(?:\s+(Bytes|Lines))?", comment)
    if m:
        count = int(m.group(1))
        if m.group(2) == "Lines":
            for _ in range(count):
                nl = text.find("\n", pos)
                if nl == -1:
                    return len(text)
                pos = nl + 1
            return pos
        return pos + count
    return pos


def as_number(token):
    return float(token) if NUMBER_RE.match(token) else None


def matches(values, target, tolerance):
    return all(v is not None and abs(v - t) <= tolerance for v, t in zip(values, target))


def replace_magenta(text, rgb_ops, cmyk_ops, spot_name, tolerance):
    """Remplace chaque réglage magenta pur par le ton direct. Renvoie (texte, nombre)."""
    replacement = spot_color_code(spot_name)
    recent = []  # derniers jetons : (début, fin, valeur numérique ou None)
    edits = []
    for start, end, token in tokenize(text):
        if token in rgb_ops or token in cmyk_ops:
            target = MAGENTA_RVB if token in rgb_ops else MAGENTA_CMJN
            operands = recent[-len(target):]
            if len(operands) == len(target) and matches([v for _, _, v in operands], target, tolerance):
                edits.append((operands[0][0], end))
                recent.clear()
                continue
        recent.append((start, end, as_number(token)))
        del recent[:-4]

    parts, last = [], 0
    for start, end in edits:
        parts += [text[last:start], replacement]
        last = end
    parts.append(text[last:])
    return "".join(parts), len(edits)


def update_dsc_header(text, spot_name):
    """Déclare le ton direct dans les commentaires DSC de l'en-tête."""
    newline = "\r\n" if "\r\n" in text[:200] else "\n"
    lines = text.split(newline)

    header_end = next((k for k, l in enumerate(lines) if l.startswith("%%EndComments")), None)
    if header_end is None:
        header_end = next((k for k, l in enumerate(lines[1:], 1) if not l.startswith("%")), len(lines))
    header = lines[:header_end]
    if any(f"({spot_name})" in l for l in header):
        return text

    def add(keyword, value):
        nonlocal header_end
        for k, line in enumerate(lines[:header_end]):
            if line.startswith(keyword):
                k += 1
                while k < header_end and lines[k].startswith("%%+"):
                    k += 1
                lines.insert(k, "%%+ " + value)
                break
        else:
            lines.insert(header_end, f"{keyword} {value}")
        header_end += 1

    add("%%DocumentCustomColors:", f"({spot_name})")
    add("%%CMYKCustomColor:", f"0 1 0 0 ({spot_name})")
    return newline.join(lines)


def convert_text(text, spot_name="CutContour", tolerance=0.002, rgb_extra=(), cmyk_extra=()):
    """Convertit tout le magenta pur du texte. Renvoie (texte, nombre, opérateurs reconnus)."""
    rgb_ops = {"setrgbcolor", *find_aliases(text, "setrgbcolor"), *rgb_extra}
    cmyk_ops = {"setcmykcolor", *find_aliases(text, "setcmykcolor"), *cmyk_extra}
    text, count = replace_magenta(text, rgb_ops, cmyk_ops, spot_name, tolerance)
    if count:
        text = update_dsc_header(text, spot_name)
    return text, count, (rgb_ops, cmyk_ops)


def split_dos_eps(data):
    """Sépare un EPS binaire DOS (aperçu TIFF/WMF) : renvoie (ps, wmf, tiff) ou None."""
    if not data.startswith(DOS_EPS_MAGIC):
        return None
    ps_off, ps_len, wmf_off, wmf_len, tiff_off, tiff_len = struct.unpack("<6I", data[4:28])
    return (data[ps_off:ps_off + ps_len],
            data[wmf_off:wmf_off + wmf_len],
            data[tiff_off:tiff_off + tiff_len])


def join_dos_eps(ps, wmf, tiff):
    header_size = 30
    ps_off = header_size
    wmf_off = ps_off + len(ps) if wmf else 0
    tiff_off = ps_off + len(ps) + len(wmf) if tiff else 0
    header = DOS_EPS_MAGIC + struct.pack("<6IH", ps_off, len(ps), wmf_off, len(wmf),
                                         tiff_off, len(tiff), 0xFFFF)
    return header + ps + wmf + tiff


def main():
    i18n.initialiser(sys.argv[1:])
    auteur = tr("Author: {name}", name=AUTEUR)
    parser = argparse.ArgumentParser(
        prog="CrunchCutContour",
        description=tr("Turns the pure magenta paths of an EPS or SVG file into the CutContour spot color."),
        epilog=f"{COPYRIGHT} — {auteur}", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"CrunchCutContour {VERSION}\n{COPYRIGHT}\n{auteur}",
                        help=tr("show program's version number and exit"))
    parser.add_argument("entree", nargs="?", metavar=tr("FILE"),
                        help=tr("source EPS or SVG file (without a file, the editor waits for one to be "
                                "dropped in the browser)"))
    parser.add_argument("--language", "--langue", dest="langue", choices=sorted(i18n.LANGUES),
                        help=tr("interface language (default: the system language)"))
    parser.add_argument("--auto", action="store_true",
                        help=tr("convert directly, without opening the editor"))
    parser.add_argument("--to-eps", action="store_true",
                        help=tr("SVG: only convert to EPS, without cut line (default output: <input>.eps)"))
    parser.add_argument("--no-browser", "--pas-de-navigateur", dest="pas_de_navigateur", action="store_true",
                        help=tr("editor: print the address without opening the browser"))
    parser.add_argument("--port", type=int, default=0,
                        help=tr("editor: local port to use (default: random)"))
    parser.add_argument("-o", "--output", "--sortie", dest="sortie", metavar=tr("OUTPUT"),
                        help=tr("--auto: output EPS file (default: <input>_CutContour.eps)"))
    parser.add_argument("-f", "--force", action="store_true",
                        help=tr("overwrite the output file if it exists"))
    parser.add_argument("--name", "--nom", dest="nom", default="CutContour", metavar=tr("NAME"),
                        help=tr("spot color name (default: CutContour)"))
    parser.add_argument("--tolerance", type=float, default=0.002, metavar="T",
                        help=tr("tolerance on each color component, 0..1 (default: 0.002)"))
    parser.add_argument("--op-rgb", "--op-rvb", dest="op_rvb", action="append", default=[], metavar=tr("NAME"),
                        help=tr("additional RGB operator to recognize (repeatable)"))
    parser.add_argument("--op-cmyk", "--op-cmjn", dest="op_cmjn", action="append", default=[], metavar=tr("NAME"),
                        help=tr("additional CMYK operator to recognize (repeatable)"))
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.nom):
        parser.error(tr("--name may only contain letters, digits, “_”, “.” or “-”"))

    if (args.auto or args.to_eps) and not args.entree:
        parser.error(tr("--auto and --to-eps require an input file"))
    if not (args.auto or args.to_eps):
        import eps_editeur
        eps_editeur.run(args.entree, args.nom, args.tolerance,
                        browser=not args.pas_de_navigateur, port=args.port)
        return

    try:
        with open(args.entree, "rb") as fh:
            data = fh.read()
    except OSError as e:
        sys.exit(tr("Error: cannot read {file} ({reason}).", file=args.entree,
                    reason=e.strerror or e))

    svg = svg_eps.est_svg(data, args.entree)
    if args.to_eps and not svg:
        parser.error(tr("--to-eps only applies to SVG files"))
    suffixe = ".eps" if args.to_eps else "_CutContour.eps"
    sortie = args.sortie or os.path.splitext(args.entree)[0] + suffixe
    if os.path.abspath(sortie) == os.path.abspath(args.entree):
        parser.error(tr("the output file must be different from the input file"))
    if os.path.exists(sortie) and not args.force:
        parser.error(tr("{file} already exists (use --force to overwrite it)", file=sortie))

    if svg:
        try:
            eps, avertissements = svg_eps.convertir(data, os.path.basename(args.entree))
        except svg_eps.SvgError as e:
            sys.exit(tr("Error: {reason}", reason=e))
        for message in avertissements:
            print(tr("Warning: {message}", message=message), file=sys.stderr)
        data = eps.encode("latin-1")
        if args.to_eps:
            with open(sortie, "wb") as fh:
                fh.write(data)
            print(tr("SVG converted to EPS -> {file}", file=sortie))
            return

    dos_parts = split_dos_eps(data)
    ps_bytes = dos_parts[0] if dos_parts else data
    if not ps_bytes.startswith(b"%!PS"):
        sys.exit(tr("Error: {file} is not a PostScript/EPS file.", file=args.entree))

    # latin-1 garde une correspondance octet <-> caractère : les données binaires survivent.
    text = ps_bytes.decode("latin-1")

    text, count, (rgb_ops, cmyk_ops) = convert_text(text, args.nom, args.tolerance,
                                                    args.op_rvb, args.op_cmjn)
    if count == 0:
        sys.exit(tr("No pure magenta found in {file}: nothing was written.", file=args.entree)
                 + "\n" + tr("Recognized operators: RGB {rgb}, CMYK {cmyk}",
                              rgb=sorted(rgb_ops), cmyk=sorted(cmyk_ops)))

    if re.search(r"^%%LanguageLevel:\s*1\b", text, re.M):
        print(tr("Warning: the file declares PostScript level 1; the Separation color space requires level 2."), file=sys.stderr)

    ps_bytes = text.encode("latin-1")
    out = join_dos_eps(ps_bytes, *dos_parts[1:]) if dos_parts else ps_bytes
    with open(sortie, "wb") as fh:
        fh.write(out)

    print(tr("{n} magenta setting(s) converted to {spot} -> {file}", n=count, spot=args.nom, file=sortie))


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        # Exécutable lancé d'un double-clic : garder la fenêtre ouverte sur un message d'erreur.
        try:
            main()
        except SystemExit as e:
            if e.code not in (None, 0):
                if isinstance(e.code, str):
                    print(e.code, file=sys.stderr)
                try:
                    input("\n" + tr("Press Enter to close this window."))
                except (EOFError, KeyboardInterrupt):
                    pass  # pas de clavier (lancé par un script) : on ferme directement
                raise SystemExit(1) from None
            raise
    else:
        main()
