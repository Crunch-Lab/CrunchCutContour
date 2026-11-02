# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests de la conversion SVG -> EPS (svg_eps.py) et de son intégration.

Lancer : python3 -m unittest discover tests
"""

import gzip
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
import svg_eps  # noqa: E402

MM = 72 / 25.4  # points par millimètre


def svg(contenu, attributs='width="100mm" height="50mm" viewBox="0 0 100 50"'):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'{attributs}>{contenu}</svg>').encode()


def traces(donnees):
    eps, avertissements = svg_eps.convertir(donnees)
    paints, erreur = interp.interpret(eps)
    if erreur:
        raise AssertionError(erreur)
    return paints, avertissements, eps


def boite(paint):
    pts = [pt for seg in paint.segments for pt in seg[1:]]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


class Chemins(unittest.TestCase):
    def setUp(self):
        i18n.choisir("en")

    def test_commandes_relatives_et_absolues(self):
        segs = svg_eps._chemin("M10 10 h20 v20 H10 z m5 5 l1 1")
        self.assertEqual(segs, [("M", 10, 10), ("L", 30, 10), ("L", 30, 30), ("L", 10, 30), ("Z",),
                                ("M", 15, 15), ("L", 16, 16)])

    def test_nombres_compacts(self):
        segs = svg_eps._chemin("M1.5.5-1-2 2e1,3")
        self.assertEqual(segs, [("M", 1.5, 0.5), ("L", -1, -2), ("L", 20, 3)])

    def test_drapeaux_d_arc_colles(self):
        a = svg_eps._chemin("M0 0 a10 10 0 0 1 20 0")
        b = svg_eps._chemin("M0 0a10,10,0,0120,0")
        self.assertEqual(a, b)

    def test_arc_demi_cercle(self):
        segs = svg_eps._chemin("M0 0 A10 10 0 0 1 20 0")
        self.assertEqual(len(segs), 3)  # moveto + deux quarts de cercle
        milieu = segs[1][5:7]           # fin du premier quart de cercle
        self.assertAlmostEqual(milieu[0], 10, places=6)
        self.assertAlmostEqual(milieu[1], -10, places=6)
        self.assertEqual(segs[-1][5:7], (20, 0))

    def test_courbes_lissees_et_quadratiques(self):
        segs = svg_eps._chemin("M0 0 C0 10 10 10 10 0 S20 -10 20 0 Q25 10 30 0 T40 0")
        self.assertEqual(segs[2][1:3], (10, -10))   # S : reflet du point de contrôle précédent
        self.assertEqual(len(segs), 5)

    def test_donnees_invalides_tronquees(self):
        self.assertEqual(svg_eps._chemin("M0 0 L10 10 L oops"), [("M", 0, 0), ("L", 10, 10)])


class Conversion(unittest.TestCase):
    def setUp(self):
        i18n.choisir("en")

    def test_rectangle_en_millimetres(self):
        paints, _, eps = traces(svg('<rect x="10" y="10" width="20" height="10" fill="red"/>'))
        self.assertIn("%%BoundingBox: 0 0 284 142", eps)
        self.assertEqual(len(paints), 1)
        x0, y0, x1, y1 = boite(paints[0])
        self.assertAlmostEqual(x0, 10 * MM, places=2)
        self.assertAlmostEqual(x1, 30 * MM, places=2)
        self.assertAlmostEqual(y0, (50 - 20) * MM, places=2)   # y inversé : le haut du SVG en haut de la page
        self.assertAlmostEqual(y1, (50 - 10) * MM, places=2)
        self.assertEqual(paints[0].rgb, (1.0, 0.0, 0.0))

    def test_formes_et_proprietes(self):
        paints, _, _ = traces(svg(
            '<circle cx="50" cy="25" r="10" fill="blue" stroke="#000" stroke-width="2"/>'
            '<ellipse cx="20" cy="20" rx="5" ry="3"/>'
            '<line x1="0" y1="0" x2="10" y2="10" stroke="green"/>'
            '<polyline points="0,0 10,0 10,10" fill="none" stroke="black"/>'
            '<polygon points="0,0 10,0 10,10" fill="yellow" fill-rule="evenodd"/>'))
        self.assertEqual([p.kind for p in paints], ["fill", "stroke", "fill", "stroke", "stroke", "eofill"])
        x0, _, x1, _ = boite(paints[0])
        self.assertAlmostEqual(x1 - x0, 20 * MM, places=2)
        self.assertAlmostEqual(paints[1].width, 2 * MM, places=3)
        self.assertTrue(all(p.editable for p in paints))

    def test_transformations_groupes_et_use(self):
        paints, _, _ = traces(svg(
            '<defs><rect id="carre" width="10" height="10"/></defs>'
            '<g transform="translate(20 0) scale(2)"><use xlink:href="#carre" x="5"/></g>'))
        x0, _, x1, _ = boite(paints[0])
        self.assertAlmostEqual(x0, 30 * MM, places=2)
        self.assertAlmostEqual(x1, 50 * MM, places=2)

    def test_feuille_de_style_et_heritage(self):
        paints, _, _ = traces(svg(
            '<style>.a{fill:#00ff00} #b{fill:rgb(0,0,255)} rect{stroke:none}</style>'
            '<g fill="red"><rect class="a" width="1" height="1"/><rect id="b" width="1" height="1"/>'
            '<rect width="1" height="1"/><rect class="a" style="fill:hsl(0,100%,50%)" width="1" height="1"/></g>'))
        self.assertEqual([p.rgb for p in paints], [(0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)])

    def test_viewbox_centree(self):
        # viewBox carrée dans une page 2:1 : centrée horizontalement (xMidYMid meet).
        paints, _, _ = traces(svg('<rect width="10" height="10"/>',
                                  'width="200" height="100" viewBox="0 0 10 10"'))
        x0, _, x1, _ = boite(paints[0])
        self.assertAlmostEqual(x0, 50 * 0.75, places=3)
        self.assertAlmostEqual(x1, 150 * 0.75, places=3)

    def test_magenta_devient_ligne_de_decoupe(self):
        _, _, eps = traces(svg('<path d="M0 0H10V10Z" fill="none" stroke="#f0f"/>'
                               '<path d="M0 0H5" fill="none" stroke="magenta"/>'))
        _, n, _ = conv.convert_text(eps)
        self.assertEqual(n, 2)

    def test_elements_masques_ignores(self):
        paints, _, _ = traces(svg('<rect width="1" height="1" display="none"/>'
                                  '<g style="display:none"><rect width="1" height="1"/></g>'
                                  '<rect width="1" height="1" fill-opacity="0"/><rect width="1" height="1"/>'))
        self.assertEqual(len(paints), 1)

    def test_avertissements(self):
        _, avert, _ = traces(svg(
            '<defs><linearGradient id="d"><stop offset="0" stop-color="#000"/>'
            '<stop offset="1" stop-color="#fff"/></linearGradient></defs>'
            '<rect width="1" height="1" fill="url(#d)"/><text>abc</text><rect width="1" height="1" opacity=".5"/>'))
        texte = " ".join(avert)
        for mot in ("Text", "Gradients", "Transparency"):
            self.assertIn(mot, texte)

    def test_degrade_remplace_par_couleur_moyenne(self):
        paints, _, _ = traces(svg(
            '<linearGradient id="d"><stop stop-color="#000"/><stop stop-color="#fff"/></linearGradient>'
            '<rect width="1" height="1" fill="url(#d)"/>'))
        for c in paints[0].rgb:
            self.assertAlmostEqual(c, 0.5, places=2)

    def test_transparence_melangee_au_blanc(self):
        paints, _, _ = traces(svg(
            '<radialGradient id="ombre"><stop stop-color="#000" stop-opacity=".5"/>'
            '<stop stop-color="#000" stop-opacity="0"/></radialGradient>'
            '<rect width="1" height="1" fill="url(#ombre)"/>'
            '<rect width="1" height="1" fill="#000" opacity=".25"/>'
            '<rect width="1" height="1" fill="none" stroke="#f0f"/>'))
        for c in paints[0].rgb:
            self.assertAlmostEqual(c, 0.75, places=2)   # ombre noire très transparente : gris clair
        for c in paints[1].rgb:
            self.assertAlmostEqual(c, 0.75, places=2)
        self.assertEqual(paints[2].rgb, (1.0, 0.0, 1.0))  # magenta opaque intact

    def test_svgz(self):
        paints, _, _ = traces(gzip.compress(svg('<rect width="1" height="1"/>')))
        self.assertEqual(len(paints), 1)

    def test_fichiers_refuses(self):
        with self.assertRaises(svg_eps.SvgError):
            svg_eps.convertir(b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "x">]><svg/>')
        with self.assertRaises(svg_eps.SvgError):
            svg_eps.convertir(b"<svg><rect></svg>")
        with self.assertRaises(svg_eps.SvgError):
            svg_eps.convertir(b"<html/>")

    def test_detection(self):
        self.assertTrue(svg_eps.est_svg(b"", "logo.SVG"))
        self.assertTrue(svg_eps.est_svg(b'<?xml version="1.0"?>\n<svg xmlns="..."/>'))
        self.assertFalse(svg_eps.est_svg(b"%!PS-Adobe-3.0 EPSF-3.0\n"))

    def test_sortie_ascii(self):
        _, _, eps = traces(svg('<rect width="1" height="1"/>'))
        eps.encode("ascii")


class Integration(unittest.TestCase):
    def setUp(self):
        i18n.choisir("en")
        self.dossier = tempfile.TemporaryDirectory()
        self.svg = os.path.join(self.dossier.name, "logo.svg")
        with open(self.svg, "wb") as fh:
            fh.write(svg('<rect width="20" height="20" fill="#ccc" stroke="#ff00ff"/>'
                         '<circle cx="50" cy="25" r="10" fill="black"/>'))

    def tearDown(self):
        self.dossier.cleanup()

    def lancer(self, *args):
        return subprocess.run([sys.executable, os.path.join(RACINE, "crunchcutcontour.py"), "--language", "en",
                               *args], capture_output=True, text=True, timeout=60)

    def test_ligne_de_commande_to_eps(self):
        r = self.lancer("--to-eps", self.svg)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.dossier.name, "logo.eps"), encoding="latin-1") as fh:
            self.assertTrue(fh.read().startswith("%!PS-Adobe-3.0 EPSF-3.0"))

    def test_ligne_de_commande_auto(self):
        r = self.lancer("--auto", self.svg)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.dossier.name, "logo_CutContour.eps"), encoding="latin-1") as fh:
            self.assertIn("/Separation /CutContour", fh.read())

    def test_to_eps_refuse_un_eps(self):
        eps = os.path.join(self.dossier.name, "a.eps")
        with open(eps, "w") as fh:
            fh.write("%!PS-Adobe-3.0 EPSF-3.0\n")
        self.assertNotEqual(self.lancer("--to-eps", eps).returncode, 0)

    def test_editeur(self):
        with open(self.svg, "rb") as fh:
            ed = eps_editeur.Editeur(fh.read(), "logo.svg", None, "CutContour", 0.002)
        self.assertTrue(ed.svg)
        self.assertEqual([p.kind for p in ed.paints], ["fill", "stroke", "fill"])
        self.assertTrue(ed.magenta(ed.paints[1]))
        seul = ed.save([], "eps", "logo.eps")
        self.assertTrue(seul["ok"], seul)
        decoupe = ed.save([2], "cutcontour", "logo_CutContour.eps")   # + contour du cercle
        self.assertTrue(decoupe["ok"], decoupe)
        resultat = interp.interpret(eps_editeur.base64.b64decode(decoupe["donnees"]).decode("latin-1"))[0]
        self.assertEqual(sum(p.spot == "CutContour" for p in resultat), 2)


if __name__ == "__main__":
    unittest.main()
