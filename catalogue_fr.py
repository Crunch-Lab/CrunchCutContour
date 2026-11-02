# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
# SPDX-License-Identifier: GPL-3.0-or-later
"""Traduction française de l'interface.

CATALOGUE : texte anglais du code -> texte français. Les {noms} entre accolades sont
remplacés par des valeurs et doivent être recopiés tels quels.
ARGPARSE : textes anglais du module argparse (aide et erreurs de la ligne de commande).
"""

SEPARATEUR_DECIMAL = ","

CATALOGUE = {
    "--auto and --to-eps require an input file":
        "--auto et --to-eps demandent un fichier d'entrée",
    "--auto, --to-eps: crop the page to the drawing":
        "--auto, --to-eps : recadrer la page sur le dessin",
    "--auto: output EPS file (default: <input>_CutContour.eps)":
        "--auto : fichier EPS produit (défaut : <entree>_CutContour.eps)",
    "--crop-margin must be zero or positive":
        "--marge doit être positive ou nulle",
    "--crop: margin around the drawing, in mm (default: 0)":
        "--recadrer : marge autour du dessin, en mm (défaut : 0)",
    "--name may only contain letters, digits, “_”, “.” or “-”":
        "--nom ne doit contenir que des lettres, chiffres, « _ », « . » ou « - »",
    "--to-eps only applies to SVG files":
        "--to-eps ne s'applique qu'aux fichiers SVG",
    "Added cut":
        "Coupe ajoutée",
    "added cut — click to undo":
        "coupe ajoutée — cliquer pour annuler",
    "additional CMYK operator to recognize (repeatable)":
        "opérateur CMJN supplémentaire à reconnaître (répétable)",
    "additional RGB operator to recognize (repeatable)":
        "opérateur RVB supplémentaire à reconnaître (répétable)",
    "Author: {name}":
        "Auteur : {name}",
    "Cancel cropping":
        "Annuler le recadrage",
    "Check failed: some paths did not turn magenta. Nothing was written.":
        "Vérification échouée : certains tracés ne sont pas passés en magenta. Rien n'a été écrit.",
    "Choose a file…":
        "Choisir un fichier…",
    "click to add a magenta outline":
        "cliquer pour lui ajouter un contour magenta",
    "click to turn it magenta":
        "cliquer pour le passer en magenta",
    "Clipping paths and masks are ignored.":
        "Les découpes (clip-path) et les masques sont ignorés.",
    "comparison: numbers or strings expected":
        "comparaison : nombres ou chaînes attendus",
    "convert directly, without opening the editor":
        "convertir directement, sans ouvrir l'éditeur",
    "Converted SVG, without cut line":
        "SVG converti, sans ligne de découpe",
    "Crop the page":
        "Recadrer la page",
    "Crop to the drawing":
        "Recadrer sur le dessin",
    "Crop…":
        "Recadrer…",
    "Deselect all":
        "Tout désélectionner",
    "division by zero":
        "division par zéro",
    "Downloaded ({format}): {name}":
        "Téléchargé ({format}) : {name}",
    "Drag it from your file manager, or choose it.":
        "Glissez-le depuis l'explorateur de fichiers, ou choisissez-le.",
    "Drag the edges or corners of the blue frame to adjust it.":
        "Faites glisser les bords ou les coins du cadre bleu pour l'ajuster.",
    "Drop an EPS or SVG file here":
        "Déposez un fichier EPS ou SVG ici",
    "Drop the EPS or SVG file to open it":
        "Déposez le fichier EPS ou SVG pour l'ouvrir",
    "Editor running at: {url}":
        "Éditeur ouvert sur : {url}",
    "Editor stopped. You can close this tab.":
        "Éditeur arrêté. Vous pouvez fermer cet onglet.",
    "editor: local port to use (default: random)":
        "éditeur : port local à utiliser (défaut : aléatoire)",
    "editor: print the address without opening the browser":
        "éditeur : afficher l'adresse sans ouvrir le navigateur",
    "Embedded images are not converted.":
        "Les images incorporées ne sont pas converties.",
    "end of image data not found":
        "fin des données d'image introuvable",
    "EPS only":
        "EPS seul",
    "Error: cannot read {file} ({reason}).":
        "Erreur : impossible de lire {file} ({reason}).",
    "Error: {file} is not a PostScript/EPS file.":
        "Erreur : {file} n'est pas un fichier PostScript/EPS.",
    "Error: {reason}":
        "Erreur : {reason}",
    "executing a string is not supported":
        "exécution d'une chaîne non gérée",
    "execution took too long (infinite loop?)":
        "exécution trop longue (boucle infinie ?)",
    "Fade artwork":
        "Estomper le dessin",
    "FILE":
        "FICHIER",
    "File not opened":
        "Fichier non ouvert",
    "File not saved":
        "Fichier non enregistré",
    "File too large or invalid request.":
        "Fichier trop volumineux ou requête invalide.",
    "fill":
        "aplat",
    "Filters (blur, shadow…) are ignored.":
        "Les filtres (flou, ombre…) sont ignorés.",
    "Fit":
        "Ajuster",
    "Fit to drawing":
        "Ajuster au dessin",
    "Gradients and patterns are replaced by a flat color.":
        "Les dégradés et les motifs sont remplacés par une couleur unie.",
    "image data read by a procedure is not supported":
        "données d'image lues par une procédure non gérée",
    "image data with the {filter} filter is not supported":
        "données d'image avec le filtre {filter} non gérées",
    "interface language (default: the system language)":
        "langue de l'interface (défaut : celle du système)",
    "Internet Explorer cannot display the editor: open the address above in Chrome, Firefox or Edge.":
        "Internet Explorer ne peut pas afficher l'éditeur : ouvrez l'adresse ci-dessus dans Chrome, Firefox ou Edge.",
    "Invalid crop frame.":
        "Cadre de recadrage invalide.",
    "Invalid file name: use a plain name ending in .eps.":
        "Nom de fichier invalide : un simple nom terminé par .eps.",
    "invalid hexadecimal string":
        "chaîne hexadécimale invalide",
    "Invalid SVG file ({reason}).":
        "Fichier SVG invalide ({reason}).",
    "Invalid SVGZ file ({reason}).":
        "Fichier SVGZ invalide ({reason}).",
    "Keep this window open while you work.":
        "Gardez cette fenêtre ouverte pendant l'utilisation.",
    "Language":
        "Langue",
    "line {line}: exit/stop outside a loop":
        "ligne {line} : exit/stop hors d'une boucle",
    "line {line}: invalid operand for {op} ({error})":
        "ligne {line} : opérande invalide pour {op} ({error})",
    "line {line}: recursion too deep":
        "ligne {line} : récursion trop profonde",
    "line {line}: {error}":
        "ligne {line} : {error}",
    "logical operation: booleans or integers expected":
        "opération logique : booléens ou entiers attendus",
    "License: {license} (free software, see LICENSE)":
        "Licence : {license} (logiciel libre, voir LICENSE)",
    "Margin":
        "Marge",
    "Markers (arrowheads…) are ignored.":
        "Les marqueurs (pointes de flèche…) sont ignorés.",
    "NAME":
        "NOM",
    "No file given: drop an EPS file onto the page in your browser.":
        "Aucun fichier indiqué : déposez un fichier EPS dans la page du navigateur.",
    "No file is open.":
        "Aucun fichier ouvert.",
    "No new path selected: nothing to save.":
        "Aucun nouveau tracé sélectionné : rien à enregistrer.",
    "No path to convert: nothing to save.":
        "Aucun tracé à convertir : rien à enregistrer.",
    "No pure magenta found in {file}: nothing was written.":
        "Aucun magenta pur trouvé dans {file} : rien n'a été écrit.",
    "No readable path in “{name}” ({error}).":
        "Aucun tracé lisible dans « {name} » ({error}).",
    "No readable path in “{name}”.":
        "Aucun tracé lisible dans « {name} ».",
    "No thanks":
        "Non merci",
    "non-invertible matrix":
        "matrice non inversible",
    "Not editable":
        "Non modifiable",
    "not editable":
        "non modifiable",
    "nothing to crop, the drawing is empty.":
        "rien à recadrer, le dessin est vide.",
    "One file at a time: only the first one is opened.":
        "Un seul fichier à la fois : seul le premier est ouvert.",
    "Open another file…":
        "Ouvrir un autre fichier…",
    "Open this address in Chrome, Firefox or Edge:":
        "Ouvrez cette adresse dans Chrome, Firefox ou Edge :",
    "Or drop an EPS or SVG file anywhere on the page":
        "Ou déposez un fichier EPS ou SVG n'importe où dans la page",
    "Original cut":
        "Coupe d'origine",
    "original cut (already in the file)":
        "coupe d'origine (déjà dans le fichier)",
    "OUTPUT":
        "SORTIE",
    "Output file name":
        "Nom du fichier de sortie",
    "overwrite the output file if it exists":
        "écraser le fichier de sortie s'il existe",
    "Page cropped to the drawing (applied when saving):":
        "Page recadrée sur le dessin (appliqué à l'enregistrement) :",
    "Page cropped to the drawing: {w} × {h} mm":
        "Page recadrée sur le dessin : {w} × {h} mm",
    "Page cropped to the frame (applied when saving):":
        "Page recadrée sur le cadre (appliqué à l'enregistrement) :",
    "Page not found":
        "Page introuvable",
    "Path #{n} — {type} — {color} — {state}":
        "Tracé n°{n} — {type} — {color} — {state}",
    "Press Ctrl+C or the “Quit” button to stop.":
        "Ctrl+C ou le bouton « Quitter » pour arrêter.",
    "Press Enter to close this window.":
        "Appuyez sur Entrée pour fermer cette fenêtre.",
    "Pure magenta":
        "Magenta pur",
    "pure magenta":
        "magenta pur",
    "Quit":
        "Quitter",
    "Reading “{name}”…":
        "Lecture de « {name} »…",
    "Recognized operators: RGB {rgb}, CMYK {cmyk}":
        "Opérateurs reconnus : RVB {rgb}, CMJN {cmyk}",
    "resource not found: {name} ({category})":
        "ressource introuvable : {name} ({category})",
    "Save":
        "Enregistrer",
    "Saved ({format}): {path}":
        "Enregistré ({format}) : {path}",
    "Saved ({format}, existing file replaced): {path}":
        "Enregistré ({format}, fichier remplacé) : {path}",
    "Saving…":
        "Enregistrement…",
    "show program's version number and exit":
        "afficher la version et quitter",
    "source EPS or SVG file (without a file, the editor waits for one to be dropped in the browser)":
        "fichier EPS ou SVG source (sans fichier : l'éditeur attend un dépôt dans le navigateur)",
    "spot color name (default: CutContour)":
        "nom du ton direct (défaut : CutContour)",
    "spot color {name}":
        "ton direct {name}",
    "SVG converted to EPS -> {file}":
        "SVG converti en EPS -> {file}",
    "SVG file converted to EPS.":
        "Fichier SVG converti en EPS.",
    "SVG file too large.":
        "Fichier SVG trop volumineux.",
    "SVG files that declare XML entities are not supported.":
        "Les fichiers SVG qui déclarent des entités XML ne sont pas pris en charge.",
    "SVG: only convert to EPS, without cut line (default output: <input>.eps)":
        "SVG : convertir seulement en EPS, sans ligne de découpe (sortie par défaut : <entree>.eps)",
    "Text is not converted: turn it into paths (outlines) before exporting the SVG.":
        "Le texte n'est pas converti : vectorisez-le (texte en tracés) avant d'exporter le SVG.",
    "The file could only be partly read ({error}). The paths shown can still be used.":
        "Lecture incomplète du fichier ({error}). Les tracés affichés restent utilisables.",
    "The frame cuts the drawing: what is outside will be removed.":
        "Le cadre coupe le dessin : ce qui dépasse sera supprimé.",
    "The output file cannot be read back ({error}): nothing was written.":
        "Le fichier produit ne se relit pas ({error}) : rien n'a été écrit.",
    "the output file must be different from the input file":
        "le fichier de sortie doit être différent du fichier d'entrée",
    "The output file must have a different name from the open file.":
        "Le fichier de sortie doit avoir un autre nom que le fichier ouvert.",
    "The page ({page}) is larger than the drawing ({drawing}). Crop the page to the drawing?":
        "La page ({page}) est plus grande que le dessin ({drawing}). Recadrer la page sur le dessin ?",
    "The server is not responding ({reason}).":
        "Le serveur ne répond pas ({reason}).",
    "The SVG contains no shape that can be converted.":
        "Le SVG ne contient aucune forme convertible.",
    "The SVG has no usable size (width/height).":
        "Le SVG n'a pas de dimensions utilisables (width/height).",
    "This browser is too old for the editor (Internet Explorer is not supported).":
        "Ce navigateur est trop ancien pour l'éditeur (Internet Explorer n'est pas pris en charge).",
    "This is not an SVG file (root element: {tag}).":
        "Ce n'est pas un fichier SVG (élément racine : {tag}).",
    "This path cannot be changed on its own: it is painted by an instruction shared with other paths.":
        "Ce tracé ne peut pas être modifié seul : il est peint par une instruction partagée avec d'autres.",
    "This path is already pure magenta in the file.":
        "Ce tracé est déjà en magenta pur dans le fichier.",
    "tolerance on each color component, 0..1 (default: 0.002)":
        "écart toléré sur chaque composante 0..1 (défaut : 0.002)",
    "Transparency is approximated: semi-transparent colors are blended with white.":
        "La transparence est approchée : les couleurs semi-transparentes sont mélangées avec du blanc.",
    "Turns the pure magenta paths of an EPS or SVG file into the CutContour spot color.":
        "Transforme les tracés magenta pur d'un EPS ou d'un SVG en ton direct CutContour.",
    "unexpected character “{char}”":
        "caractère inattendu « {char} »",
    "unknown name: {name}":
        "nom inconnu : {name}",
    "Unknown save mode.":
        "Mode d'enregistrement inconnu.",
    "unterminated ASCII85 string":
        "chaîne ASCII85 non terminée",
    "unterminated hexadecimal string":
        "chaîne hexadécimale non terminée",
    "unterminated string":
        "chaîne non terminée",
    "Warning: the file could only be partly read ({error}).":
        "Attention : lecture incomplète du fichier ({error}).",
    "Warning: the file declares PostScript level 1; the Separation color space requires level 2.":
        "Attention : le fichier se déclare PostScript niveau 1 ; l'espace Separation requiert le niveau 2.",
    "Warning: {message}":
        "Attention : {message}",
    "Zoom in":
        "Zoom avant",
    "Zoom out":
        "Zoom arrière",
    "{file} already exists (use --force to overwrite it)":
        "{file} existe déjà (utilisez --force pour l'écraser)",
    "{name} — in your browser's download folder":
        "{name} — dans le dossier de téléchargement du navigateur",
    "{n} magenta setting(s) converted to {spot} -> {file}":
        "{n} réglage(s) magenta converti(s) en {spot} -> {file}",
    "{n} path(s) read from {name} (dropped in the browser).":
        "{n} tracé(s) lus dans {name} (déposé dans le navigateur).",
    "{n} path(s) read from {name}.":
        "{n} tracé(s) lus dans {name}.",
    "{n} paths. Click an outline to turn it pure magenta; click again to undo.":
        "{n} tracés. Cliquez sur un contour pour le passer en magenta pur ; recliquez pour annuler.",
    "{op}: array, dictionary or string expected":
        "{op} : tableau, dictionnaire ou chaîne attendu",
    "{op}: boolean expected, found {type}":
        "{op} : booléen attendu, trouvé {type}",
    "{op}: dictionary expected":
        "{op} : dictionnaire attendu",
    "{op}: dictionary stack is empty":
        "{op} : pile de dictionnaires vide",
    "{op}: end of encrypted section not found":
        "{op} : fin de la partie chiffrée introuvable",
    "{op}: file access is not supported":
        "{op} : accès aux fichiers non géré",
    "{op}: invalid operand":
        "{op} : opérande invalide",
    "{op}: matrix expected":
        "{op} : matrice attendue",
    "{op}: no current path":
        "{op} : pas de tracé courant",
    "{op}: no current point":
        "{op} : pas de point courant",
    "{op}: no mark":
        "{op} : pas de marque",
    "{op}: number expected":
        "{op} : nombre attendu",
    "{op}: number expected, found {type}":
        "{op} : nombre attendu, trouvé {type}",
    "{op}: odd number of elements":
        "{op} : nombre impair d'éléments",
    "{op}: only direct reading of currentfile is supported":
        "{op} : seule la lecture directe de currentfile est gérée",
    "{op}: procedure expected, found {type}":
        "{op} : procédure attendue, trouvé {type}",
    "{op}: stack is empty":
        "{op} : pile vide",
    "{op}: stack too short":
        "{op} : pile trop courte",
    "{op}: unknown key {key}":
        "{op} : clé inconnue {key}",
    "{width} pt stroke":
        "trait de {width} pt",
    "{w} × {h} mm":
        "{w} × {h} mm",
    "“{name}” is not an EPS file (it does not start with %!PS).":
        "« {name} » n'est pas un fichier EPS (il ne commence pas par %!PS).",
    "“{name}” is not an EPS or SVG file (.eps or .svg extension expected).":
        "« {name} » n'est pas un fichier EPS ou SVG (extension .eps ou .svg attendue).",
    "“{name}”: {reason}":
        "« {name} » : {reason}",
    "“{” without “}”":
        "« { » sans « } »",
    "“}” without “{”":
        "« } » sans « { »",
    "✓ File saved":
        "✓ Fichier bien enregistré",
}

ARGPARSE = {
    "usage: ": "utilisation : ",
    "positional arguments": "arguments positionnels",
    "optional arguments": "options",
    "options": "options",
    "show this help message and exit": "afficher cette aide et quitter",
    "show program's version number and exit": "afficher la version et quitter",
    "%(prog)s: error: %(message)s\n": "%(prog)s : erreur : %(message)s\n",
    "unrecognized arguments: %s": "arguments non reconnus : %s",
    "the following arguments are required: %s": "arguments obligatoires manquants : %s",
    "expected one argument": "un argument attendu",
    "invalid %(type)s value: %(value)r": "valeur %(type)s invalide : %(value)r",
    "argument %(argument_name)s: %(message)s": "argument %(argument_name)s : %(message)s",
    "invalid choice: %(value)r (choose from %(choices)s)": "choix invalide : %(value)r (possibles : %(choices)s)",
    "ambiguous option: %(option)s could match %(matches)s": "option ambiguë : %(option)s peut correspondre à %(matches)s",
}
