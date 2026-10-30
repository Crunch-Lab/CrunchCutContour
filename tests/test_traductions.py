# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
"""Vérifie que chaque texte de l'interface est traduit dans chaque langue.

Les textes sont relevés dans le code : tr("…") en Python, t("…") en JavaScript et
[[…]] en HTML (pages de eps_editeur.py). Lancer : python3 -m unittest discover tests
"""

import ast
import json
import os
import re
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import i18n  # noqa: E402

FICHIERS = ["crunchcutcontour.py", "eps_editeur.py", "eps_interpreteur.py", "svg_eps.py"]
JS_T = re.compile(r'\bt\("((?:[^"\\]|\\.)*)"')
HTML = re.compile(r"\[\[(.+?)\]\]")
VARIABLE = re.compile(r"\{(\w+)\}")
POURCENT = re.compile(r"%\((\w+)\)[sdr]|%[sdr]")


def textes_du_code():
    """{texte anglais: [emplacements]} pour tous les textes traduisibles."""
    textes = {}
    for nom in FICHIERS:
        with open(os.path.join(RACINE, nom), encoding="utf-8") as fh:
            arbre = ast.parse(fh.read())
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Call) and getattr(noeud.func, "id", None) == "tr" and noeud.args:
                arg = noeud.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    textes.setdefault(arg.value, []).append(f"{nom}:{noeud.lineno}")
            elif isinstance(noeud, ast.Constant) and isinstance(noeud.value, str):
                for m in JS_T.finditer(noeud.value):
                    textes.setdefault(json.loads('"' + m.group(1) + '"'), []).append(f"{nom} (JS)")
                for m in HTML.finditer(noeud.value):
                    textes.setdefault(m.group(1), []).append(f"{nom} (HTML)")
    return textes


class Traductions(unittest.TestCase):
    textes = textes_du_code()
    langues = [code for code in i18n.LANGUES if code != i18n.SOURCE]

    def test_textes_trouves(self):
        self.assertGreater(len(self.textes), 100)

    def test_tout_est_traduit(self):
        for code in self.langues:
            catalogue = i18n.LANGUES[code][1].CATALOGUE
            manquants = sorted(t for t in self.textes if t not in catalogue)
            self.assertEqual(manquants, [], f"textes sans traduction en « {code} »")

    def test_pas_de_traduction_orpheline(self):
        for code in self.langues:
            catalogue = i18n.LANGUES[code][1].CATALOGUE
            orphelins = sorted(t for t in catalogue if t not in self.textes)
            self.assertEqual(orphelins, [], f"traductions « {code} » qui ne servent plus")

    def test_memes_variables(self):
        for code in self.langues:
            for source, traduit in i18n.LANGUES[code][1].CATALOGUE.items():
                self.assertEqual(set(VARIABLE.findall(source)), set(VARIABLE.findall(traduit)),
                                 f"« {code} » : variables différentes dans {source!r}")
            for source, traduit in i18n.LANGUES[code][1].ARGPARSE.items():
                self.assertEqual(sorted(POURCENT.findall(source)), sorted(POURCENT.findall(traduit)),
                                 f"« {code} » : variables argparse différentes dans {source!r}")

    def test_source_sans_catalogue(self):
        self.assertEqual(i18n.LANGUES[i18n.SOURCE][1].CATALOGUE, {})


class Langue(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        i18n.choisir(i18n.SOURCE)

    def test_detection_par_variable_d_environnement(self):
        for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
            os.environ.pop(var, None)
        os.environ["LANG"] = "fr_CA.UTF-8"
        self.assertEqual(i18n.detecter(), "fr")
        os.environ["LANG"] = "en_US.UTF-8"
        self.assertEqual(i18n.detecter(), "en")

    def test_langue_non_disponible(self):
        for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES"):
            os.environ.pop(var, None)
        os.environ["LANG"] = "de_DE.UTF-8"
        self.assertIn(i18n.detecter(), i18n.LANGUES)
        self.assertFalse(i18n.choisir("xx"))

    def test_option_prioritaire(self):
        os.environ["LANG"] = "en_US.UTF-8"
        i18n.initialiser(["--langue", "fr"])
        self.assertEqual(i18n.langue(), "fr")
        i18n.initialiser(["--language", "en"])
        self.assertEqual(i18n.langue(), "en")

    def test_traduction_avec_variables(self):
        i18n.choisir("fr")
        self.assertEqual(i18n.tr("{n} path(s) read from {name}.", n=3, name="a.eps"),
                         "3 tracé(s) lus dans a.eps.")
        i18n.choisir("en")
        self.assertEqual(i18n.tr("{n} path(s) read from {name}.", n=3, name="a.eps"),
                         "3 path(s) read from a.eps.")

    def test_separateur_decimal(self):
        i18n.choisir("fr")
        self.assertEqual(i18n.nombre(84.5), "84,5")
        i18n.choisir("en")
        self.assertEqual(i18n.nombre(84.5), "84.5")

    def test_texte_inconnu_rendu_tel_quel(self):
        i18n.choisir("fr")
        self.assertEqual(i18n.tr("not in any catalog"), "not in any catalog")


if __name__ == "__main__":
    unittest.main()
