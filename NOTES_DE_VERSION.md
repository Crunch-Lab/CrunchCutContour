CrunchCutContour prépare des fichiers EPS ou SVG pour les imprimantes-découpeuses : les contours
choisis à la souris deviennent une ligne de découpe (ton direct **CutContour**, magenta pur).
Chaque fichier ci-dessous est autonome : rien à installer. Logiciel libre et gratuit, sous
licence GPL version 3 ou ultérieure.

## Dans cette version

- **Éditeur dans le navigateur** : cliquez sur un contour pour en faire une ligne de découpe ; un
  aplat cliqué reçoit un contour de découpe qui suit sa forme. Une légende distingue les coupes
  d'origine, les coupes ajoutées et les tracés non modifiables.
- **Enregistrement** en CutContour (ton direct) ou en magenta pur ; le fichier ouvert n'est
  jamais modifié.
- **Import SVG** : un fichier SVG ou SVGZ est converti en EPS à l'ouverture ; `--to-eps` fait
  une simple conversion SVG → EPS.
- **Recadrage de la page** : proposé quand la page est plus grande que le dessin, ou à tout
  moment avec **Recadrer…** ; cadre automatique avec marge, ou ajusté à la souris.
- **Interface en français et en anglais**, selon la langue du système (`--language`).
- **Conversion en ligne de commande** : `--auto` transforme tout le magenta pur en CutContour.

## Quel fichier télécharger ?

| Système | Fichier |
|---|---|
| Windows 7 SP1, 8, 8.1 (32 ou 64 bits) | `CrunchCutContour-{{VERSION}}-windows7-8-x86.exe` |
| Windows 10, 11 (64 bits) | `CrunchCutContour-{{VERSION}}-windows10-11-x64.exe` |
| macOS, Mac Intel | `CrunchCutContour-{{VERSION}}-macos-x86_64.zip` |
| macOS, Mac Apple Silicon (M1, M2…) | `CrunchCutContour-{{VERSION}}-macos-arm64.zip` |
| Linux 64 bits (Ubuntu 22.04, Debian 12, Fedora 36 ou plus récent) | `CrunchCutContour-{{VERSION}}-linux-x86_64.tar.gz` |

La version Windows 7/8 fonctionne aussi sous Windows 10 et 11, mais elle embarque Python 3.8,
qui n'est plus mis à jour : sous Windows 10 et 11, préférez la version 10/11.

## Utilisation

- **Lancer le programme sans fichier** (double-clic) : le navigateur s'ouvre et attend qu'on y
  dépose un fichier EPS ou SVG. Le résultat est téléchargé dans le dossier de téléchargement.
- **Glisser un fichier sur l'icône** (Windows) ou `CrunchCutContour fichier.eps` (terminal) :
  l'éditeur s'ouvre sur ce fichier ; le résultat est enregistré à côté de l'original.
- **Sans éditeur** :
  `CrunchCutContour --auto fichier.eps` (ligne de découpe à partir du magenta pur),
  `CrunchCutContour --to-eps logo.svg` (conversion SVG → EPS),
  `--crop --crop-margin 2` pour recadrer la page sur le dessin avec 2 mm de marge.
- La fenêtre de terminal reste ouverte pendant l'utilisation : la fermer, ou cliquer sur
  **Quitter** dans la page, arrête le programme.

## Premier lancement

- **Windows** : l'exécutable n'est pas signé. Si SmartScreen s'affiche, cliquez sur
  « Informations complémentaires » puis « Exécuter quand même ».
- **Windows 7** : il faut Windows 7 SP1 à jour (mises à jour KB2533623 et KB2999226, installées
  par Windows Update) et Chrome ou Firefox : Internet Explorer ne peut pas afficher l'éditeur.
- **macOS** : décompressez le zip, puis faites un clic droit sur `CrunchCutContour-…` → **Ouvrir**
  (ou, si macOS refuse, Réglages Système → Confidentialité et sécurité → **Ouvrir quand même**).
  Le programme s'ouvre dans le Terminal.
- **Linux** : `tar -xzf CrunchCutContour-{{VERSION}}-linux-x86_64.tar.gz` puis
  `./CrunchCutContour-{{VERSION}}-linux-x86_64`.

## Limites

Les EPS « simples » (Inkscape, cairo, exports courants) sont pris en charge ; certains EPS
d'Illustrator très complexes peuvent ne s'afficher qu'en partie (un bandeau le signale). Le
texte n'est ni affiché ni converti depuis un SVG : vectorisez-le avant l'export. Les images
n'apparaissent que comme un cadre gris ; les dégradés SVG deviennent une couleur unie.

---

Copyright © 2026 UTBM CrunchLab — Auteur : Alexandre Willaume — Licence GPL-3.0-or-later
