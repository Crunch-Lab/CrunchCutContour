@echo off
rem Copyright (c) 2026 UTBM CrunchLab
rem Auteur : Alexandre Willaume
rem Construit les executables Windows autonomes (Python inclus) dans dist\ :
rem   construire_exe.bat win7    CrunchCutContour-<version>-windows7-8-x86.exe
rem                              Windows 7 SP1, 8 et 8.1 (32 et 64 bits) ; Python 3.8 32 bits,
rem                              derniere version de Python qui fonctionne sous Windows 7.
rem   construire_exe.bat win10   CrunchCutContour-<version>-windows10-11-x64.exe
rem                              Windows 10 et 11 (64 bits) ; Python 3.13, maintenu.
rem   construire_exe.bat         les deux.
rem Chaque Python est telecharge depuis nuget.org dans un sous-dossier (python38, python313) :
rem rien n'est installe sur le systeme.
setlocal
cd /d "%~dp0"

if "%~1"=="" (
    call "%~f0" win7 || exit /b 1
    call "%~f0" win10 || exit /b 1
    exit /b 0
)

if /i "%~1"=="win7" (
    set PKG=pythonx86
    set PYVER=3.8.10
    set PYDIR=python38
    set PYINST=pyinstaller==5.13.2
    set CIBLE=windows7-8-x86
) else if /i "%~1"=="win10" (
    set PKG=python
    set PYVER=3.13.17
    set PYDIR=python313
    set PYINST=pyinstaller==6.22.3
    set CIBLE=windows10-11-x64
) else (
    echo Cible inconnue : %~1 ^(win7 ou win10^)
    exit /b 1
)
set PY=%PYDIR%\tools\python.exe

if not exist %PY% (
    echo Telechargement de %PKG% %PYVER%...
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = 'Tls12'; Invoke-WebRequest -UseBasicParsing 'https://api.nuget.org/v3-flatcontainer/%PKG%/%PYVER%/%PKG%.%PYVER%.nupkg' -OutFile %PYDIR%.zip; Expand-Archive -Force %PYDIR%.zip %PYDIR%" || exit /b 1
    del %PYDIR%.zip
)
%PY% -m pip --version >nul 2>&1 || %PY% -m ensurepip --default-pip || exit /b 1
%PY% -m pip install --quiet --disable-pip-version-check --no-warn-script-location "%PYINST%" || exit /b 1

for /f "delims=" %%v in ('%PY% -c "import crunchcutcontour; print(crunchcutcontour.VERSION)"') do set VERSION=%%v
set NOM=CrunchCutContour-%VERSION%-%CIBLE%

if not exist build\%CIBLE% mkdir build\%CIBLE%
%PY% version_windows.py "%~dp0build\%CIBLE%\version.txt" %NOM%.exe || exit /b 1

%PY% -m PyInstaller --noconfirm --clean --onefile --console --name %NOM% ^
    --workpath build\%CIBLE% --specpath build\%CIBLE% ^
    --version-file "%~dp0build\%CIBLE%\version.txt" ^
    --hidden-import eps_editeur --hidden-import eps_interpreteur crunchcutcontour.py || exit /b 1

echo.
echo Executable : %~dp0dist\%NOM%.exe
