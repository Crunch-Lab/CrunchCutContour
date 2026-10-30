#!/bin/sh
# Construit l'exécutable autonome macOS ou Linux (Python inclus) dans dist/ :
#   dist/EPS_CutContour-<version>-<macos|linux>-<arch>        l'exécutable
#   dist/EPS_CutContour-<version>-<macos|linux>-<arch>.zip    (macOS) ou .tar.gz (Linux)
# PyInstaller est installé dans un environnement isolé (venv-build), pas dans le système.
# Python utilisé : $PYTHON, sinon python3. L'exécutable vise l'architecture de ce Python.
set -eu
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python3}

case "$(uname -s)" in
    Darwin) OS=macos ;;
    Linux) OS=linux ;;
    *) echo "Système non géré : $(uname -s)" >&2; exit 1 ;;
esac
ARCH=$("$PYTHON" -c "import platform; print(platform.machine())")
VERSION=$("$PYTHON" -c "import eps_cutcontour; print(eps_cutcontour.VERSION)")
NOM="EPS_CutContour-$VERSION-$OS-$ARCH"

[ -x venv-build/bin/python ] || "$PYTHON" -m venv venv-build
venv-build/bin/python -m pip install --quiet --disable-pip-version-check "pyinstaller==6.22.3"

venv-build/bin/python -m PyInstaller --noconfirm --clean --onefile --console --name "$NOM" \
    --workpath "build/$OS-$ARCH" --specpath "build/$OS-$ARCH" \
    --hidden-import eps_editeur --hidden-import eps_interpreteur eps_cutcontour.py

cd dist
if [ "$OS" = macos ]; then
    rm -f "$NOM.zip"
    ditto -c -k --keepParent "$NOM" "$NOM.zip"   # conserve le droit d'exécution
    echo "Archive : $(pwd)/$NOM.zip"
else
    tar -czf "$NOM.tar.gz" "$NOM"
    echo "Archive : $(pwd)/$NOM.tar.gz"
fi
