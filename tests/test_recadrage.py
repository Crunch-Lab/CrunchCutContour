# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests du recadrage de la page sur le dessin.

Lancer : python3 -m unittest discover tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import crunchcutcontour as conv  # noqa: E402
import eps_editeur  # noqa: E402
import eps_interpreteur as interp  # noqa: E402
import i18n  # noqa: E402

EPS = """%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 200 100
%%EndComments
%%BeginSetup
%%PageBoundingBox: 0 0 200 100
%%EndSetup
1 0 0 setrgbcolor
50 50 10 0 360 arc closepath fill
0 0 1 setrgbcolor 4 setlinewidth
100 20 moveto 150 20 lineto stroke
showpage
"""


class Boite(unittest.TestCase):
    def test_bezier_exacte(self):
        # Quart de cercle : les points de contrôle dépassent, pas la courbe.
        b = interp._bezier_bounds((0, 0), (0, 10), (10, 20), (20, 20))
        self.assertEqual(b, (0, 0, 20, 20))
        b = interp._bezier_bounds((0, 0), (10, 30), (20, 30), (30, 0))
        self.assertAlmostEqual(b[3], 22.5)   # sommet de la courbe, sous les points de contrôle (30)

    def test_boite_du_dessin(self):
        paints, _ = interp.interpret(EPS)
        b = interp.content_box(paints)
        self.assertEqual(tuple(round(v, 6) for v in b), (40, 18, 152, 60))   # trait de 4 : ± 2

    def test_cadre_limite_a_la_page(self):
        self.assertEqual(interp.crop_box(EPS, 50), (0, 0, 200, 100))
        self.assertIsNone(interp.crop_box("%!PS\n%%BoundingBox: 0 0 10 10\n", 0))


class Reecriture(unittest.TestCase):
    def test_boites_reecrites(self):
        t = conv.recadrer(EPS, (39.5, 17.25, 152.5, 60))
        self.assertIn("%%BoundingBox: 39 17 153 60\n", t)
        self.assertIn("%%HiResBoundingBox: 39.5 17.25 152.5 60\n", t)
        self.assertIn("%%PageBoundingBox: 39 17 153 60\n", t)
        self.assertEqual(interp.bounding_box(t), (39.5, 17.25, 152.5, 60))
        # Le dessin est inchangé.
        self.assertEqual(t.replace("39 17 153 60", "0 0 200 100").replace("%%HiResBoundingBox: 39.5 17.25 152.5 60\n", ""),
                         EPS)

    def test_boite_absente_ajoutee(self):
        t = conv.recadrer("%!PS-Adobe-3.0 EPSF-3.0\n%%EndComments\n0 0 moveto\n", (1, 2, 3, 4))
        self.assertTrue(t.startswith("%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 1 2 3 4\n%%HiResBoundingBox: 1 2 3 4\n"))

    def test_eps_incorpore_et_atend(self):
        src = ("%!PS-Adobe-3.0 EPSF-3.0\r\n%%BoundingBox: (atend)\r\n%%EndComments\r\n"
               "%%BeginDocument: a.eps\r\n%%BoundingBox: 5 5 6 6\r\n%%EndDocument\r\n"
               "%%Trailer\r\n%%BoundingBox: 0 0 100 100\r\n")
        t = conv.recadrer(src, (10, 10, 20, 20))
        self.assertEqual(t.count("%%BoundingBox: 10 10 20 20"), 2)   # en-tête et trailer
        self.assertIn("%%BoundingBox: 5 5 6 6\r\n", t)              # EPS incorporé intact
        self.assertNotIn("\n%%", t.replace("\r\n", ""))             # fins de ligne CRLF conservées


class Decoupe(unittest.TestCase):
    def test_placement(self):
        t = conv.ajouter_decoupe(EPS, (10, 20, 110, 70))
        lignes = t.split("\n")
        self.assertEqual(lignes[lignes.index("%%EndComments") + 1], "gsave 10 20 100 50 rectclip")
        self.assertEqual(lignes[-2], "grestore")       # avant la dernière ligne vide
        self.assertIsNone(interp.interpret(t)[1])

    def test_avant_le_trailer(self):
        t = conv.ajouter_decoupe("%!PS\n%%EndComments\nx\n%%Trailer\n%%EOF\n", (0, 0, 1, 1))
        self.assertIn("x\ngrestore\n%%Trailer", t)


class Integration(unittest.TestCase):
    def setUp(self):
        i18n.choisir("en")
        self.dossier = tempfile.TemporaryDirectory()
        self.svg = os.path.join(self.dossier.name, "logo.svg")
        with open(self.svg, "w") as fh:
            fh.write('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 100 50">'
                     '<rect x="10" y="10" width="20" height="20" fill="none" stroke="#f0f"/></svg>')

    def tearDown(self):
        self.dossier.cleanup()

    def lancer(self, *args):
        return subprocess.run([sys.executable, os.path.join(RACINE, "crunchcutcontour.py"), "--language", "en", *args],
                              capture_output=True, text=True, timeout=60)

    def boite(self, nom):
        with open(os.path.join(self.dossier.name, nom), encoding="latin-1") as fh:
            return interp.bounding_box(fh.read())

    def test_ligne_de_commande(self):
        r = self.lancer("--auto", "--crop", "--crop-margin", "2", self.svg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("25.0 × 25.0 mm", r.stdout)   # carré de 20 mm + trait de 1 mm + 2 × 2 mm de marge
        x0, y0, x1, y1 = self.boite("logo_CutContour.eps")
        self.assertAlmostEqual((x1 - x0) / conv.MM, 25, places=3)

    def test_marge_negative_refusee(self):
        self.assertNotEqual(self.lancer("--to-eps", "--crop", "--crop-margin", "-1", self.svg).returncode, 0)

    def test_editeur(self):
        with open(self.svg, "rb") as fh:
            ed = eps_editeur.Editeur(fh.read(), "logo.svg", None, "CutContour", 0.002)
        self.assertFalse(ed.save([], "eps", "a.eps", recadrage=-1)["ok"])
        self.assertFalse(ed.save([], "eps", "a.eps", recadrage="2")["ok"])
        r = ed.save([], "eps", "a.eps", recadrage=0)
        texte = eps_editeur.base64.b64decode(r["donnees"]).decode("latin-1")
        x0, y0, x1, y1 = interp.bounding_box(texte)
        self.assertAlmostEqual((x1 - x0) / conv.MM, 21, places=2)   # coordonnées arrondies au millième de pt
        # Cadre ajusté à la souris : sans découpe s'il englobe le dessin, avec sinon.
        lire = lambda r: eps_editeur.base64.b64decode(r["donnees"]).decode("latin-1")
        # Carré du SVG : x de 26,9 à 86,5 pt, y de 55,3 à 114,8 pt (trait compris).
        englobe = lire(ed.save([], "eps", "a.eps", recadrage={"boite": [20, 50, 100, 120]}))
        self.assertNotIn("gsave 20 50 80 70 rectclip", englobe)
        self.assertEqual(interp.bounding_box(englobe), (20, 50, 100, 120))
        coupe = lire(ed.save([], "eps", "a.eps", recadrage={"boite": [40, 40, 100, 100]}))
        self.assertIn("gsave 40 40 60 60 rectclip", coupe)
        self.assertIsNone(interp.interpret(coupe)[1])
        # Cadre limité à la page ; cadres invalides refusés.
        page = lire(ed.save([], "eps", "a.eps", recadrage={"boite": [-50, -50, 1000, 1000]}))
        for v, attendu in zip(interp.bounding_box(page), (0, 0, 283.4646, 141.7323)):
            self.assertAlmostEqual(v, attendu, places=2)   # boîte écrite au millième de point
        for invalide in ({"boite": [10, 10, 5, 50]}, {"boite": [1, 2, 3]}, {"boite": "x"}, {"marge": True},
                         {"boite": [500, 500, 600, 600]}):
            self.assertFalse(ed.save([], "eps", "a.eps", recadrage=invalide)["ok"], invalide)
        sans = eps_editeur.base64.b64decode(ed.save([], "eps", "a.eps")["donnees"]).decode("latin-1")
        self.assertIn("%%BoundingBox: 0 0 284 142", sans)


if __name__ == "__main__":
    unittest.main()
