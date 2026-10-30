CrunchCutContour transforme les contours d'un fichier EPS en ligne de découpe (ton direct
**CutContour**, magenta pur) pour les imprimantes-découpeuses. On choisit les contours à la
souris dans le navigateur. Chaque fichier ci-dessous est autonome : rien à installer.

## Quel fichier télécharger ?

| Système | Fichier |
|---|---|
| Windows 7 SP1, 8, 8.1 (32 ou 64 bits) | `CrunchCutContour-1.0.0-windows7-8-x86.exe` |
| Windows 10, 11 (64 bits) | `CrunchCutContour-1.0.0-windows10-11-x64.exe` |
| macOS, Mac Intel | `CrunchCutContour-1.0.0-macos-x86_64.zip` |
| macOS, Mac Apple Silicon (M1, M2…) | `CrunchCutContour-1.0.0-macos-arm64.zip` |
| Linux 64 bits (Ubuntu 22.04, Debian 12, Fedora 36 ou plus récent) | `CrunchCutContour-1.0.0-linux-x86_64.tar.gz` |

La version Windows 7/8 fonctionne aussi sous Windows 10 et 11, mais elle embarque Python 3.8,
qui n'est plus mis à jour : sous Windows 10 et 11, préférez la version 10/11.

## Utilisation

- **Lancer le programme sans fichier** (double-clic) : le navigateur s'ouvre et attend qu'on y
  dépose un fichier EPS. Le résultat est téléchargé dans le dossier de téléchargement.
- **Glisser un fichier EPS sur l'icône** (Windows) ou `CrunchCutContour fichier.eps` (terminal) :
  l'éditeur s'ouvre sur ce fichier ; le résultat est enregistré à côté de l'original.
- Dans l'éditeur, cliquez sur un contour pour le passer en magenta pur, puis **Enregistrer**
  en CutContour ou en magenta pur.
- Conversion sans éditeur : `CrunchCutContour --auto fichier.eps` convertit tout le magenta pur
  du fichier en CutContour.
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
- **Linux** : `tar -xzf CrunchCutContour-1.0.0-linux-x86_64.tar.gz` puis
  `./CrunchCutContour-1.0.0-linux-x86_64`.

## Limites

Les EPS « simples » (Inkscape, cairo, exports courants) sont pris en charge. Le texte n'est pas
affiché dans l'éditeur (vectorisez-le pour le voir) et les images n'apparaissent que comme un
cadre gris. Certains EPS d'Illustrator très complexes peuvent ne s'afficher qu'en partie : un
bandeau le signale.

---

Copyright © 2026 UTBM CrunchLab — Auteur : Alexandre Willaume
