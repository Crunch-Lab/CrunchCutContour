#!/usr/bin/env python3
"""Convertit les couleurs magenta pur d'un fichier EPS en ton direct CutContour.

Par défaut, le fichier s'ouvre dans un éditeur (navigateur) où l'on clique sur
les contours à passer en magenta pur avant d'enregistrer (voir eps_editeur.py).
Avec --auto, la conversion se fait directement, sans éditeur.

Le script repère dans le code PostScript chaque réglage de couleur magenta pur :
  - RVB  : 1 0 1 setrgbcolor   (ou un alias, ex. « 1 0 1 rg » dans les EPS cairo)
  - CMJN : 0 1 0 0 setcmykcolor (ou un alias)
et le remplace par un ton direct (espace Separation) nommé CutContour, rendu en
magenta pur (C0 M100 J0 N0), reconnu par les RIP d'impression-découpe
(VersaWorks, Onyx, Caldera...). Les commentaires DSC de l'en-tête sont mis à jour.

Usage :
  python3 eps_cutcontour.py [entree.eps]                     (éditeur ; sans fichier,
                                                              déposez-le dans la page)
  python3 eps_cutcontour.py --auto entree.eps [-o sortie.eps]
"""

import argparse
import os
import re
import struct
import sys

VERSION = "1.0.0"

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
    parser = argparse.ArgumentParser(
        description="Transforme les tracés magenta pur d'un EPS en ton direct CutContour.")
    parser.add_argument("--version", action="version", version=f"EPS CutContour {VERSION}")
    parser.add_argument("entree", nargs="?",
                        help="fichier EPS source (sans fichier : l'éditeur attend un dépôt dans le navigateur)")
    parser.add_argument("--auto", action="store_true",
                        help="convertir directement, sans ouvrir l'éditeur")
    parser.add_argument("--pas-de-navigateur", action="store_true",
                        help="éditeur : afficher l'adresse sans ouvrir le navigateur")
    parser.add_argument("--port", type=int, default=0,
                        help="éditeur : port local à utiliser (défaut : aléatoire)")
    parser.add_argument("-o", "--sortie",
                        help="--auto : fichier EPS produit (défaut : <entree>_CutContour.eps)")
    parser.add_argument("-f", "--force", action="store_true",
                        help="écraser le fichier de sortie s'il existe")
    parser.add_argument("--nom", default="CutContour",
                        help="nom du ton direct (défaut : CutContour)")
    parser.add_argument("--tolerance", type=float, default=0.002,
                        help="écart toléré sur chaque composante 0..1 (défaut : 0.002)")
    parser.add_argument("--op-rvb", action="append", default=[], metavar="NOM",
                        help="opérateur RVB supplémentaire à reconnaître (répétable)")
    parser.add_argument("--op-cmjn", action="append", default=[], metavar="NOM",
                        help="opérateur CMJN supplémentaire à reconnaître (répétable)")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.nom):
        parser.error("--nom ne doit contenir que des lettres, chiffres, « _ », « . » ou « - »")

    if args.auto and not args.entree:
        parser.error("--auto demande un fichier d'entrée")
    if not args.auto:
        import eps_editeur
        eps_editeur.run(args.entree, args.nom, args.tolerance,
                        browser=not args.pas_de_navigateur, port=args.port)
        return

    sortie = args.sortie or os.path.splitext(args.entree)[0] + "_CutContour.eps"
    if os.path.abspath(sortie) == os.path.abspath(args.entree):
        parser.error("le fichier de sortie doit être différent du fichier d'entrée")
    if os.path.exists(sortie) and not args.force:
        parser.error(f"{sortie} existe déjà (utilisez --force pour l'écraser)")

    with open(args.entree, "rb") as fh:
        data = fh.read()

    dos_parts = split_dos_eps(data)
    ps_bytes = dos_parts[0] if dos_parts else data
    if not ps_bytes.startswith(b"%!PS"):
        sys.exit(f"Erreur : {args.entree} n'est pas un fichier PostScript/EPS.")

    # latin-1 garde une correspondance octet <-> caractère : les données binaires survivent.
    text = ps_bytes.decode("latin-1")

    text, count, (rgb_ops, cmyk_ops) = convert_text(text, args.nom, args.tolerance,
                                                    args.op_rvb, args.op_cmjn)
    if count == 0:
        sys.exit(f"Aucun magenta pur trouvé dans {args.entree} : rien n'a été écrit.\n"
                 f"Opérateurs reconnus : RVB {sorted(rgb_ops)}, CMJN {sorted(cmyk_ops)}")

    if re.search(r"^%%LanguageLevel:\s*1\b", text, re.M):
        print("Attention : le fichier se déclare PostScript niveau 1 ; "
              "l'espace Separation requiert le niveau 2.", file=sys.stderr)

    ps_bytes = text.encode("latin-1")
    out = join_dos_eps(ps_bytes, *dos_parts[1:]) if dos_parts else ps_bytes
    with open(sortie, "wb") as fh:
        fh.write(out)

    print(f"{count} réglage(s) magenta converti(s) en {args.nom} -> {sortie}")


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
                    input("\nAppuyez sur Entrée pour fermer cette fenêtre.")
                except (EOFError, KeyboardInterrupt):
                    pass  # pas de clavier (lancé par un script) : on ferme directement
                raise SystemExit(1) from None
            raise
    else:
        main()
