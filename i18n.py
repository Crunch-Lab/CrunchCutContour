# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
# SPDX-License-Identifier: GPL-3.0-or-later
"""Traduction de l'interface.

Le texte du code, en anglais, sert de clé : tr("{n} path(s) read.", n=3) renvoie la
traduction dans la langue courante, ou le texte anglais s'il n'y en a pas. Les textes
d'argparse (« usage: », « show this help message and exit »…) sont traduits aussi.

Ajouter une langue : copier catalogue_fr.py en catalogue_xx.py, traduire chaque valeur,
puis l'inscrire dans LANGUES ci-dessous. tests/test_traductions.py vérifie qu'aucun
texte ne manque.
"""

import argparse
import locale
import os
import subprocess
import sys

import catalogue_en
import catalogue_fr

# code -> (nom de la langue dans cette langue, catalogue)
LANGUES = {
    "en": ("English", catalogue_en),
    "fr": ("Français", catalogue_fr),
}
SOURCE = "en"      # langue dans laquelle les textes sont écrits dans le code
REPLI = "en"       # langue utilisée quand celle du système n'est pas disponible

_courante = SOURCE


def tr(texte, **valeurs):
    """Traduit `texte` dans la langue courante, puis y insère `valeurs` ({nom})."""
    traduit = LANGUES[_courante][1].CATALOGUE.get(texte, texte)
    return traduit.format(**valeurs) if valeurs else traduit


def nombre(valeur, decimales=1):
    """Nombre écrit avec le séparateur décimal de la langue courante (0.5 / 0,5)."""
    texte = f"{valeur:.{decimales}f}"
    return texte.replace(".", getattr(LANGUES[_courante][1], "SEPARATEUR_DECIMAL", "."))


def langue():
    return _courante


def catalogue():
    """Textes de la langue courante (clé anglaise -> traduction), pour les pages web."""
    return dict(LANGUES[_courante][1].CATALOGUE)


def choisir(code):
    """Change la langue courante ; renvoie False si `code` n'est pas disponible."""
    global _courante
    code = (code or "").lower()
    if code not in LANGUES:
        return False
    _courante = code
    traductions = LANGUES[code][1].ARGPARSE
    argparse._ = lambda s: traductions.get(s, s)
    argparse.ngettext = lambda s, p, n: traductions.get(s if n == 1 else p, s if n == 1 else p)
    return True


def _codes_systeme():
    """Codes de langue préférés du système, du plus au moins prioritaire."""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        for valeur in os.environ.get(var, "").split(":"):
            if valeur and valeur not in ("C", "POSIX") and not valeur.startswith("C."):
                yield valeur
    if sys.platform == "win32":
        try:
            import ctypes
            ident = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if ident in locale.windows_locale:
                yield locale.windows_locale[ident]
        except (AttributeError, OSError):
            pass
    elif sys.platform == "darwin":
        try:
            sortie = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True,
                                    text=True, timeout=2).stdout
            for ligne in sortie.splitlines():
                ligne = ligne.strip(' \t",()')
                if ligne:
                    yield ligne
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        code = locale.getlocale()[0]
        if code:
            yield code
    except ValueError:
        pass


def detecter():
    """Langue du système si elle est disponible, sinon l'anglais."""
    for code in _codes_systeme():
        code = code.replace("-", "_").split("_")[0].split(".")[0].lower()
        if code in LANGUES:
            return code
    return REPLI


def initialiser(argv):
    """Choisit la langue d'après --language (ou --langue) dans `argv`, sinon d'après le système.

    À appeler avant de construire l'ArgumentParser, dont l'aide doit déjà être traduite.
    """
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--language", "--langue", dest="langue")
    demande = pre.parse_known_args(argv)[0].langue
    if not (demande and choisir(demande)):
        choisir(detecter())
    return demande
