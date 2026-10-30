# CrunchCutContour

Prépare des fichiers EPS ou SVG pour les imprimantes-découpeuses (Roland VersaWorks et les autres
logiciels de découpe qui reconnaissent le ton direct `CutContour`) : les contours choisis
deviennent une **ligne de découpe**, affichée en magenta pur (C0 M100 J0 N0). Le nom du ton
direct est réglable (`--name`) pour les logiciels qui en attendent un autre. Les fichiers SVG
sont convertis en EPS ; le programme sert aussi de simple convertisseur SVG → EPS.

On choisit les contours à la souris, dans le navigateur ; une conversion automatique est aussi
possible en ligne de commande. Le programme est écrit en Python sans aucune dépendance, et il
est distribué sous forme d'exécutables autonomes : rien à installer.

## Sommaire

- [Téléchargement](#téléchargement)
- [Utilisation](#utilisation)
- [Ligne de commande](#ligne-de-commande)
- [Ce que le programme modifie dans le fichier](#ce-que-le-programme-modifie-dans-le-fichier)
- [Import SVG](#import-svg)
- [Limites](#limites)
- [Lancer depuis les sources](#lancer-depuis-les-sources)
- [Construire les exécutables](#construire-les-exécutables)
- [Organisation du code](#organisation-du-code)
- [Auteur et droits](#auteur-et-droits)

## Téléchargement

| Système | Fichier |
|---|---|
| Windows 7 SP1, 8, 8.1 (32 ou 64 bits) | `CrunchCutContour-<version>-windows7-8-x86.exe` |
| Windows 10, 11 (64 bits) | `CrunchCutContour-<version>-windows10-11-x64.exe` |
| Mac Intel | `CrunchCutContour-<version>-macos-x86_64.zip` |
| Mac Apple Silicon (M1, M2…) | `CrunchCutContour-<version>-macos-arm64.zip` |
| Linux 64 bits (glibc 2.35 ou plus : Ubuntu 22.04, Debian 12, Fedora 36…) | `CrunchCutContour-<version>-linux-x86_64.tar.gz` |

La version Windows 7/8 fonctionne aussi sous Windows 10 et 11, mais elle embarque Python 3.8,
qui ne reçoit plus de correctifs : sous Windows 10 et 11, prenez la version 10/11.

### Premier lancement

- **Windows** : les exécutables ne sont pas signés. Si SmartScreen s'affiche, cliquez sur
  « Informations complémentaires » puis « Exécuter quand même ».
- **Windows 7** : il faut Windows 7 SP1 à jour (mises à jour KB2533623 et KB2999226, fournies
  par Windows Update ; la seconde est aussi installée par tout « Visual C++ 2015+
  Redistributable »), et Chrome (109 au plus) ou Firefox ESR. Internet Explorer ne peut pas
  afficher l'éditeur : s'il est le navigateur par défaut, le programme ouvre Chrome, Firefox ou
  Edge à sa place.
- **macOS** : décompressez le zip, puis clic droit sur le fichier → **Ouvrir**. Si macOS refuse,
  allez dans Réglages Système → Confidentialité et sécurité → **Ouvrir quand même**. Le
  programme s'ouvre dans le Terminal.
- **Linux** :
  ```bash
  tar -xzf CrunchCutContour-1.0.0-linux-x86_64.tar.gz
  ./CrunchCutContour-1.0.0-linux-x86_64
  ```

## Utilisation

### Ouvrir un fichier

- **Lancer le programme sans fichier** (double-clic) : le navigateur s'ouvre sur une page
  « Déposez un fichier EPS ou SVG ici ». Glissez-y un fichier ou choisissez-le avec le bouton.
  Le fichier doit être un EPS (`.eps`, commençant par `%!PS`) ou un SVG (`.svg`, `.svgz`) et
  contenir au moins un tracé lisible ; sinon la page indique pourquoi et attend un autre fichier.
- **Glisser un fichier EPS ou SVG sur l'icône de l'exécutable** (Windows), ou le donner en
  argument (`CrunchCutContour fichier.eps`) : l'éditeur s'ouvre directement sur ce fichier.

Un SVG est converti en EPS dès l'ouverture (voir [Import SVG](#import-svg)) ; un bandeau
signale ce qui n'a pas pu être converti (texte, dégradés…).

Une fenêtre de terminal reste ouverte pendant l'utilisation : la fermer, faire Ctrl+C ou
cliquer sur **Quitter** dans la page arrête le programme.

### Choisir les contours

- **Survol** : le tracé visé est entouré de bleu ; la barre du bas indique son numéro, son type,
  sa couleur et son épaisseur.
- **Clic sur un trait** : il passe en magenta pur. Un nouveau clic annule.
- **Clic sur un aplat** : il garde sa couleur et reçoit un contour magenta fin (0,25 pt) qui
  suit sa forme.
- **Légende** (sous la barre d'outils), avec le nombre de tracés de chaque sorte :

  | Repère | Signification |
  |---|---|
  | Magenta continu | **Coupe d'origine** : déjà en magenta pur ou CutContour dans le fichier |
  | Magenta à pointillés blancs | **Coupe ajoutée** dans l'éditeur |
  | Pointillés gris | **Non modifiable** : tracé peint par une instruction partagée avec d'autres |

- **Estomper le dessin** : met le dessin en transparence pour faire ressortir les coupes.
- **Zoom** : boutons − / Ajuster / +, ou Ctrl + molette.
- **Tout désélectionner** retire les coupes ajoutées ; **Ouvrir un autre fichier…** (ou un
  dépôt n'importe où dans la page) remplace le document, sans demander de confirmation.

### Enregistrer

Choisissez le format puis cliquez sur **Enregistrer** :

- **CutContour** (par défaut) : les coupes deviennent le ton direct `CutContour`, reconnu par
  les logiciels de découpe. Le magenta pur déjà présent dans le fichier est converti aussi.
- **Magenta pur** : les contours choisis passent en magenta RVB pur, sans ton direct (pour un
  logiciel qui fait lui-même la conversion, ou pour retoucher le fichier ailleurs).
- **EPS seul** (fichiers SVG uniquement) : le SVG converti en EPS, sans ligne de découpe.

Le nom proposé est `<nom>_CutContour.eps`, `<nom>_magenta.eps` ou `<nom>.eps` ; il est
modifiable. Le fichier ouvert n'est jamais modifié.

- **Fichier donné en argument** : le résultat est écrit à côté de l'original. Un fichier de même
  nom est remplacé, et le message le signale.
- **Fichier déposé dans le navigateur** : le navigateur ne communique pas son dossier, le
  résultat est donc téléchargé (dossier de téléchargement du navigateur).

Avant d'écrire, le programme relit le fichier produit et vérifie que chaque contour choisi est
bien en magenta ; sinon rien n'est écrit. Un bandeau vert « ✓ Fichier bien enregistré » ou
rouge « Fichier non enregistré » confirme le résultat.

## Ligne de commande

```
CrunchCutContour [options] [fichier.eps | fichier.svg]
```

Depuis les sources, remplacez `CrunchCutContour` par `python3 crunchcutcontour.py`.

| Option | Effet |
|---|---|
| *(sans fichier)* | Éditeur : attend qu'on dépose un fichier dans la page |
| `fichier.eps`, `fichier.svg` | Éditeur ouvert sur ce fichier |
| `--auto` | Conversion directe, sans éditeur : tout le magenta pur devient CutContour |
| `--to-eps` | SVG : conversion en EPS seulement, sans ligne de découpe (défaut : `<fichier>.eps`) |
| `-o`, `--output FICHIER` | Avec `--auto` : fichier produit (défaut : `<fichier>_CutContour.eps`) |
| `-f`, `--force` | Avec `--auto` : écraser le fichier produit s'il existe |
| `--name NOM` | Nom du ton direct (défaut : `CutContour`) |
| `--tolerance T` | Écart toléré sur chaque composante de couleur, de 0 à 1 (défaut : 0.002) |
| `--op-rgb NOM`, `--op-cmyk NOM` | Avec `--auto` : opérateur de couleur supplémentaire à reconnaître (répétable) |
| `--language en\|fr` | Langue de l'interface (défaut : celle du système) |
| `--no-browser` | Éditeur : afficher l'adresse sans ouvrir le navigateur |
| `--port PORT` | Éditeur : port local à utiliser (défaut : aléatoire) |
| `--version` | Afficher la version |

Les noms français des options de la version 1.0.0 restent acceptés : `--sortie`, `--nom`,
`--op-rvb`, `--op-cmjn`, `--langue`, `--pas-de-navigateur`.

Exemples :

```bash
CrunchCutContour --auto stickers.eps
```

```bash
CrunchCutContour --auto stickers.eps -o pret_a_decouper.eps --force
```

```bash
CrunchCutContour --to-eps logo.svg
```

## Langues

L'interface (ligne de commande, aide, messages, pages de l'éditeur) existe en **anglais** et en
**français**. La langue est choisie dans cet ordre :

1. l'option `--language` (`--language fr`, `--language en`) ;
2. la langue du système (variables `LANGUAGE`, `LC_ALL`, `LC_MESSAGES`, `LANG`, langue de
   l'interface Windows, langues préférées de macOS) ;
3. l'anglais, si la langue du système n'est pas disponible.

Dans l'éditeur, le menu de langue en haut à droite change la langue de la page et des
messages ; la sélection en cours est conservée.

En mode `--auto`, si le fichier ne contient aucun magenta pur, rien n'est écrit et le
programme se termine avec le code 1.

## Ce que le programme modifie dans le fichier

Le programme ne touche que ce qui est nécessaire ; le reste du fichier est recopié à l'octet
près (fins de ligne, données binaires, aperçu TIFF/WMF des EPS « DOS » compris).

- **Couleur de découpe** : chaque réglage de couleur concerné est remplacé par un espace couleur
  PostScript niveau 2
  ```
  [/Separation /CutContour /DeviceCMYK {0 exch 0 0}] setcolorspace 1 setcolor
  ```
  c'est-à-dire un ton direct `CutContour` qui s'affiche en magenta pur.
- **Magenta pur reconnu** : `1 0 1 setrgbcolor` et `0 1 0 0 setcmykcolor`, ainsi que leurs
  alias définis dans le fichier (par exemple `rg` dans les EPS produits par cairo et Inkscape).
  Les textes, commentaires et données d'image ne sont jamais modifiés.
- **Contour choisi dans l'éditeur** : l'instruction qui le peint est entourée d'un réglage de
  couleur dans un `gsave … grestore`, ce qui ne change rien au reste du dessin.
- **En-tête** : le ton direct est déclaré dans les commentaires DSC (`%%DocumentCustomColors`
  et `%%CMYKCustomColor`), en conservant les autres tons directs déjà déclarés.

## Import SVG

Un SVG est converti en EPS (PostScript niveau 2) par le programme lui-même, sans logiciel
externe. Une forme du SVG devient un tracé de l'EPS, sélectionnable seul dans l'éditeur. Un
contour **magenta pur** (`#ff00ff`, `magenta`, `fuchsia`) dans le SVG devient directement une
ligne de découpe : préparez-le dans Inkscape ou Illustrator, puis `--auto`.

- **Pris en charge** : `path` (toutes les commandes, arcs compris), `rect` (coins arrondis),
  `circle`, `ellipse`, `line`, `polyline`, `polygon` ; groupes, `use` et `symbol`, `svg`
  imbriqués, `switch` ; transformations ; couleurs nommées, `#rgb`, `#rrggbb`, `rgb()`,
  `hsl()`, `currentColor` ; remplissage (règle `evenodd` comprise) et contour (épaisseur,
  jointures, extrémités, pointillés) ; feuilles `<style>` simples (sélecteurs de type,
  `.classe`, `#id` : c'est la forme des exports Illustrator) ; `viewBox`,
  `preserveAspectRatio` et unités (`mm`, `cm`, `in`, `pt`, `px`…) ; fichiers `.svgz`.
- **Approché** : les dégradés et motifs deviennent une couleur unie (moyenne du dégradé) ; la
  transparence est simulée en mélangeant la couleur avec du blanc.
- **Non converti** (un avertissement le signale) : le texte (vectorisez-le avant l'export), les
  images, les découpes et masques, les filtres, les marqueurs.
- La taille de la page vient de `width` et `height` du SVG (1 px = 0,75 pt), ou à défaut de sa
  `viewBox`.
- Par sécurité, les SVG qui déclarent des entités XML (`<!ENTITY …>`) sont refusés.

## Limites

- Pour afficher le fichier, le programme exécute lui-même le code PostScript avec un
  interpréteur simplifié. Les EPS « simples » (Inkscape, cairo, la plupart des exports) sont pris
  en charge ; certains EPS d'Illustrator très complexes peuvent ne s'afficher qu'en partie. Un
  bandeau le signale, et les tracés affichés restent utilisables.
- Le texte n'est pas affiché : vectorisez-le avant l'export pour le voir et le sélectionner.
- Les images n'apparaissent que comme un cadre gris et ne sont pas sélectionnables.
- Un tracé peint par une instruction qui en peint plusieurs (une boucle, par exemple) ne peut
  pas être modifié seul.
- L'éditeur demande un navigateur récent (Chrome, Firefox, Edge, Safari) ; Internet Explorer
  n'est pas pris en charge.
- L'espace couleur utilisé demande un RIP PostScript niveau 2 ou plus (c'est le cas de tous
  les logiciels de découpe actuels).

## Lancer depuis les sources

Il suffit de Python 3.8 ou plus récent ; aucune dépendance.

```bash
python3 crunchcutcontour.py
```

L'éditeur est un petit serveur HTTP local : il n'écoute que sur `127.0.0.1`, sur un port
aléatoire, et chaque requête doit porter un jeton secret tiré au lancement. Il n'est donc pas
accessible depuis le réseau ni depuis une autre page web. Sous WSL, la page s'ouvre dans le
navigateur de Windows.

### Tests

```bash
python3 -m unittest discover tests
```

### Ajouter une langue

Les textes sont écrits en anglais dans le code : `tr("…")` en Python, `t("…")` en
JavaScript et `[[…]]` dans le HTML des pages ([eps_editeur.py](eps_editeur.py)). Le texte
anglais sert de clé de traduction.

1. Copier [catalogue_fr.py](catalogue_fr.py) en `catalogue_xx.py` (`xx` : code ISO 639-1 de
   la langue, par exemple `de`) et traduire chaque valeur. Les `{noms}` entre accolades sont
   remplacés par des valeurs : les recopier tels quels.
2. Inscrire le module dans `LANGUES`, dans [i18n.py](i18n.py).
3. Lancer les tests : ils signalent tout texte non traduit, toute traduction qui ne sert
   plus et toute variable `{…}` oubliée.

Un nouveau texte dans le code doit être ajouté à chaque catalogue ; les tests le rappellent.

## Construire les exécutables

Les exécutables sont produits avec [PyInstaller](https://pyinstaller.org) dans le dossier
`dist/`. PyInstaller ne fait pas de compilation croisée : chaque système se construit sur
lui-même.

- **Windows** : sous Windows, depuis le dossier du projet
  ```bat
  construire_exe.bat win7
  construire_exe.bat win10
  ```
  Sans argument, il construit les deux. Le script télécharge le Python nécessaire depuis
  nuget.org dans un sous-dossier (`python38` : Python 3.8.10 32 bits, `python313` : Python
  3.13 64 bits) et y installe PyInstaller : rien n'est installé sur le système.
- **macOS et Linux** :
  ```bash
  sh construire.sh
  ```
  Il utilise `python3` (ou la variable `PYTHON`), installe PyInstaller dans `venv-build/`, et
  produit l'exécutable pour l'architecture de ce Python, plus une archive `.zip` (macOS) ou
  `.tar.gz` (Linux). Sous Linux, l'exécutable ne tourne que sur les systèmes dont la glibc est
  au moins aussi récente que celle de la machine de construction.

### Publier une release

Le workflow [.github/workflows/release.yml](.github/workflows/release.yml) construit les
cinq fichiers (Windows 7/8, Windows 10/11, macOS Intel, macOS Apple Silicon, Linux) sur les
machines de GitHub, avec les mêmes scripts.

1. Mettre à jour `VERSION` dans [crunchcutcontour.py](crunchcutcontour.py) et
   [NOTES_DE_VERSION.md](NOTES_DE_VERSION.md).
2. Pousser l'étiquette correspondante, par exemple :
   ```bash
   git tag v1.0.0 && git push origin v1.0.0
   ```

Le workflow vérifie que l'étiquette correspond à `VERSION`, puis crée la release GitHub avec
les fichiers et les notes de version. Lancé à la main (onglet Actions), il construit seulement ;
les fichiers sont alors dans les « artifacts » de l'exécution.

## Organisation du code

| Fichier | Rôle |
|---|---|
| [crunchcutcontour.py](crunchcutcontour.py) | Point d'entrée et options ; conversion du magenta pur en CutContour (`--auto`), en-tête DSC, EPS « DOS » |
| [eps_editeur.py](eps_editeur.py) | Éditeur : serveur HTTP local, pages web (dépôt et édition), modification des contours choisis |
| [svg_eps.py](svg_eps.py) | Conversion SVG → EPS |
| [eps_interpreteur.py](eps_interpreteur.py) | Interpréteur PostScript simplifié : exécute le fichier et relève chaque tracé, sa couleur et l'instruction source qui l'a peint |
| [i18n.py](i18n.py) | Traduction : choix et détection de la langue, fonction `tr()`, traduction de l'aide d'argparse |
| [catalogue_fr.py](catalogue_fr.py), [catalogue_en.py](catalogue_en.py) | Textes de chaque langue |
| [tests/](tests) | Tests : traductions complètes, détection de la langue, conversion SVG |
| [construire_exe.bat](construire_exe.bat) | Construction des exécutables Windows |
| [construire.sh](construire.sh) | Construction des exécutables macOS et Linux |
| [version_windows.py](version_windows.py) | Propriétés des exécutables Windows (société, copyright, version) |
| [NOTES_DE_VERSION.md](NOTES_DE_VERSION.md) | Texte de la release GitHub |

## Auteur et droits

Copyright © 2026 UTBM CrunchLab.

Auteur : Alexandre Willaume.

Le nom, l'auteur et le copyright sont définis une seule fois, dans
[crunchcutcontour.py](crunchcutcontour.py) (`COPYRIGHT`, `AUTEUR`) ; ils sont repris par
`--version`, l'aide, le pied des pages de l'éditeur et les propriétés des exécutables Windows.
