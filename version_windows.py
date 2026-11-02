# Copyright © 2026 UTBM CrunchLab
# Auteur : Alexandre Willaume
# SPDX-License-Identifier: GPL-3.0-or-later
"""Écrit le fichier de version Windows passé à PyInstaller (--version-file).

Ces informations apparaissent dans Propriétés → Détails de l'exécutable : société,
copyright, version, description. Elles viennent des constantes de crunchcutcontour.py.

Usage : python version_windows.py <fichier de sortie> <nom du .exe>
"""

import sys

import crunchcutcontour as app


def contenu(nom_exe):
    nums = tuple(int(x) for x in app.VERSION.split(".")) + (0,) * 4
    nums = nums[:4]
    chaines = {
        "CompanyName": "UTBM CrunchLab",
        "FileDescription": "CrunchCutContour",
        "FileVersion": app.VERSION,
        "InternalName": "CrunchCutContour",
        "LegalCopyright": app.COPYRIGHT,
        "OriginalFilename": nom_exe,
        "ProductName": "CrunchCutContour",
        "ProductVersion": app.VERSION,
        "Comments": f"Author: {app.AUTEUR} - License: {app.LICENCE}",
    }
    lignes = ",\n".join(f"        StringStruct({k!r}, {v!r})" for k, v in chaines.items())
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
{lignes}
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
  ]
)
"""


if __name__ == "__main__":
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        fh.write(contenu(sys.argv[2]))
