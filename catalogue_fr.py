"""Traduction française de l'interface.

CATALOGUE : texte anglais du code -> texte français. Les {noms} entre accolades sont
remplacés par des valeurs et doivent être recopiés tels quels.
ARGPARSE : textes anglais du module argparse (aide et erreurs de la ligne de commande).
"""

CATALOGUE = {
    "--auto requires an input file":
        "--auto demande un fichier d'entrée",
    "--auto: output EPS file (default: <input>_CutContour.eps)":
        "--auto : fichier EPS produit (défaut : <entree>_CutContour.eps)",
    "--name may only contain letters, digits, “_”, “.” or “-”":
        "--nom ne doit contenir que des lettres, chiffres, « _ », « . » ou « - »",
    "Added cut":
        "Coupe ajoutée",
    "added cut — click to undo":
        "coupe ajoutée — cliquer pour annuler",
    "additional CMYK operator to recognize (repeatable)":
        "opérateur CMJN supplémentaire à reconnaître (répétable)",
    "additional RGB operator to recognize (repeatable)":
        "opérateur RVB supplémentaire à reconnaître (répétable)",
    "Check failed: some paths did not turn magenta. Nothing was written.":
        "Vérification échouée : certains tracés ne sont pas passés en magenta. Rien n'a été écrit.",
    "Choose a file…":
        "Choisir un fichier…",
    "click to add a magenta outline":
        "cliquer pour lui ajouter un contour magenta",
    "click to turn it magenta":
        "cliquer pour le passer en magenta",
    "comparison: numbers or strings expected":
        "comparaison : nombres ou chaînes attendus",
    "convert directly, without opening the editor":
        "convertir directement, sans ouvrir l'éditeur",
    "CutContour Editor":
        "Éditeur CutContour",
    "Deselect all":
        "Tout désélectionner",
    "division by zero":
        "division par zéro",
    "Downloaded ({format}): {name}":
        "Téléchargé ({format}) : {name}",
    "Drag it from your file manager, or choose it.":
        "Glissez-le depuis l'explorateur de fichiers, ou choisissez-le.",
    "Drop an EPS file here":
        "Déposez un fichier EPS ici",
    "Drop the EPS file to open it":
        "Déposez le fichier EPS pour l'ouvrir",
    "Editor running at: {url}":
        "Éditeur ouvert sur : {url}",
    "Editor stopped. You can close this tab.":
        "Éditeur arrêté. Vous pouvez fermer cet onglet.",
    "editor: local port to use (default: random)":
        "éditeur : port local à utiliser (défaut : aléatoire)",
    "editor: print the address without opening the browser":
        "éditeur : afficher l'adresse sans ouvrir le navigateur",
    "end of image data not found":
        "fin des données d'image introuvable",
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
    "File not opened":
        "Fichier non ouvert",
    "File not saved":
        "Fichier non enregistré",
    "File too large or invalid request.":
        "Fichier trop volumineux ou requête invalide.",
    "FILE.eps":
        "FICHIER.eps",
    "fill":
        "aplat",
    "Fit":
        "Ajuster",
    "image data read by a procedure is not supported":
        "données d'image lues par une procédure non gérée",
    "image data with the {filter} filter is not supported":
        "données d'image avec le filtre {filter} non gérées",
    "interface language (default: the system language)":
        "langue de l'interface (défaut : celle du système)",
    "Internet Explorer cannot display the editor: open the address above in Chrome, Firefox or Edge.":
        "Internet Explorer ne peut pas afficher l'éditeur : ouvrez l'adresse ci-dessus dans Chrome, Firefox ou Edge.",
    "Invalid file name: use a plain name ending in .eps.":
        "Nom de fichier invalide : un simple nom terminé par .eps.",
    "invalid hexadecimal string":
        "chaîne hexadécimale invalide",
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
    "non-invertible matrix":
        "matrice non inversible",
    "Not editable":
        "Non modifiable",
    "not editable":
        "non modifiable",
    "One file at a time: only the first one is opened.":
        "Un seul fichier à la fois : seul le premier est ouvert.",
    "Open another file…":
        "Ouvrir un autre fichier…",
    "Open this address in Chrome, Firefox or Edge:":
        "Ouvrez cette adresse dans Chrome, Firefox ou Edge :",
    "Or drop an EPS file anywhere on the page":
        "Ou déposez un fichier EPS n'importe où dans la page",
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
    "source EPS file (without a file, the editor waits for one to be dropped in the browser)":
        "fichier EPS source (sans fichier : l'éditeur attend un dépôt dans le navigateur)",
    "spot color name (default: CutContour)":
        "nom du ton direct (défaut : CutContour)",
    "spot color {name}":
        "ton direct {name}",
    "The file could only be partly read ({error}). The paths shown can still be used.":
        "Lecture incomplète du fichier ({error}). Les tracés affichés restent utilisables.",
    "The output file cannot be read back ({error}): nothing was written.":
        "Le fichier produit ne se relit pas ({error}) : rien n'a été écrit.",
    "the output file must be different from the input file":
        "le fichier de sortie doit être différent du fichier d'entrée",
    "The output file must have a different name from the open file.":
        "Le fichier de sortie doit avoir un autre nom que le fichier ouvert.",
    "The server is not responding ({reason}).":
        "Le serveur ne répond pas ({reason}).",
    "This browser is too old for the editor (Internet Explorer is not supported).":
        "Ce navigateur est trop ancien pour l'éditeur (Internet Explorer n'est pas pris en charge).",
    "This path cannot be changed on its own: it is painted by an instruction shared with other paths.":
        "Ce tracé ne peut pas être modifié seul : il est peint par une instruction partagée avec d'autres.",
    "This path is already pure magenta in the file.":
        "Ce tracé est déjà en magenta pur dans le fichier.",
    "tolerance on each color component, 0..1 (default: 0.002)":
        "écart toléré sur chaque composante 0..1 (défaut : 0.002)",
    "Turns the pure magenta paths of an EPS file into the CutContour spot color.":
        "Transforme les tracés magenta pur d'un EPS en ton direct CutContour.",
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
    "“{name}” is not an EPS file (.eps extension expected).":
        "« {name} » n'est pas un fichier EPS (extension .eps attendue).",
    "“{name}” is not an EPS file (it does not start with %!PS).":
        "« {name} » n'est pas un fichier EPS (il ne commence pas par %!PS).",
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
