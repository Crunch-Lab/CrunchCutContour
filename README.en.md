# CrunchCutContour

[Français](README.md) · **English**

Prepares EPS or SVG files for print-and-cut machines (Roland VersaWorks and other cutting
software that recognizes the `CutContour` spot color): the outlines you choose become a **cut
line**, shown in pure magenta (C0 M100 Y0 K0). The spot color name can be changed (`--name`) for
software that expects another one. SVG files are converted to EPS; the program also works as a
plain SVG → EPS converter.

You pick the outlines with the mouse, in your web browser; an automatic conversion is also
available from the command line. The program is written in Python with no dependencies and is
distributed as standalone executables: nothing to install. It is **free software**, at no cost,
licensed under the GPL version 3 or later.

## Contents

- [Download](#download)
- [Usage](#usage)
- [Command line](#command-line)
- [Languages](#languages)
- [What the program changes in the file](#what-the-program-changes-in-the-file)
- [SVG import](#svg-import)
- [Limitations](#limitations)
- [Running from source](#running-from-source)
- [Building the executables](#building-the-executables)
- [Code layout](#code-layout)
- [Author and license](#author-and-license)

## Download

| System | File |
|---|---|
| Windows 7 SP1, 8, 8.1 (32 or 64-bit) | `CrunchCutContour-<version>-windows7-8-x86.exe` |
| Windows 10, 11 (64-bit) | `CrunchCutContour-<version>-windows10-11-x64.exe` |
| Intel Mac | `CrunchCutContour-<version>-macos-x86_64.zip` |
| Apple Silicon Mac (M1, M2…) | `CrunchCutContour-<version>-macos-arm64.zip` |
| 64-bit Linux (glibc 2.35 or later: Ubuntu 22.04, Debian 12, Fedora 36…) | `CrunchCutContour-<version>-linux-x86_64.tar.gz` |

The Windows 7/8 build also runs on Windows 10 and 11, but it embeds Python 3.8, which no longer
receives fixes: on Windows 10 and 11, use the 10/11 build.

### First launch

- **Windows**: the executables are not signed. If SmartScreen appears, click "More info", then
  "Run anyway".
- **Windows 7**: requires an up-to-date Windows 7 SP1 (updates KB2533623 and KB2999226, provided
  by Windows Update; the latter is also installed by any "Visual C++ 2015+ Redistributable"),
  and Chrome (109 at most) or Firefox ESR. Internet Explorer cannot display the editor: if it is
  the default browser, the program opens Chrome, Firefox or Edge instead.
- **macOS**: unzip the file, then right-click it → **Open**. If macOS refuses, go to System
  Settings → Privacy & Security → **Open Anyway**. The program opens in Terminal.
- **Linux**:
  ```bash
  tar -xzf CrunchCutContour-1.0.0-linux-x86_64.tar.gz
  ./CrunchCutContour-1.0.0-linux-x86_64
  ```

## Usage

### Opening a file

- **Start the program without a file** (double-click): the browser opens a page saying "Drop an
  EPS or SVG file here". Drag a file onto it or pick one with the button. The file must be an
  EPS (`.eps`, starting with `%!PS`) or an SVG (`.svg`, `.svgz`) and contain at least one
  readable path; otherwise the page explains why and waits for another file.
- **Drag an EPS or SVG file onto the executable's icon** (Windows), or pass it as an argument
  (`CrunchCutContour file.eps`): the editor opens directly on that file.

An SVG is converted to EPS as soon as it is opened (see [SVG import](#svg-import)); a banner
lists anything that could not be converted (text, gradients…).

A terminal window stays open while you work: closing it, pressing Ctrl+C or clicking **Quit**
on the page stops the program.

### Choosing the outlines

- **Hover**: the path under the pointer is outlined in blue; the status bar shows its number,
  type, color and line width.
- **Click a stroke**: it turns pure magenta. Click again to undo.
- **Click a fill**: it keeps its color and gets a thin magenta outline (0.25 pt) that follows
  its shape.
- **Legend** (below the toolbar), with the number of paths of each kind:

  | Marker | Meaning |
  |---|---|
  | Solid magenta | **Original cut**: already pure magenta or CutContour in the file |
  | Magenta with white dashes | **Added cut** in the editor |
  | Grey dots | **Not editable**: path painted by an instruction shared with other paths |

- **Fade artwork**: makes the artwork translucent so the cuts stand out.
- **Zoom**: − / Fit / + buttons, or Ctrl + mouse wheel.
- **Deselect all** removes the added cuts; **Open another file…** (or dropping a file anywhere
  on the page) replaces the document, without asking for confirmation.

### Cropping the page

The **Crop…** button in the toolbar turns cropping on at any time; when the page extends more
than 1 mm beyond the artwork on any side (common with SVG files), a blue banner also suggests it.

- The frame is shown as a dashed blue line and the area outside it is greyed out. By default it
  surrounds the whole artwork (exact curves, stroke width included) with an adjustable
  **margin** in mm.
- **With the mouse**: drag the edges or corners of the frame to adjust it; **Fit to drawing**
  (or changing the margin) goes back to the automatic frame.
- The frame never extends beyond the original page. If it cuts into the artwork, a red warning
  says so: when saving, whatever lies outside is removed (PostScript clipping), cut lines
  included.
- Cropping is applied when saving; **Cancel cropping**, **No thanks** or a second click on
  **Crop…** turns it off.

### Saving

Choose the format, then click **Save**:

- **CutContour** (default): the cuts become the `CutContour` spot color, recognized by cutting
  software. Any pure magenta already in the file is converted too.
- **Pure magenta**: the chosen outlines turn pure RGB magenta, without a spot color (for
  software that does the conversion itself, or to keep editing the file elsewhere).
- **EPS only** (SVG files only): the SVG converted to EPS, without a cut line.

The suggested name is `<name>_CutContour.eps`, `<name>_magenta.eps` or `<name>.eps`; you can
change it. The opened file is never modified.

- **File given as an argument**: the result is written next to the original. A file with the
  same name is replaced, and the message says so.
- **File dropped into the browser**: the browser does not reveal its folder, so the result is
  downloaded (to the browser's download folder).

Before writing, the program reads the output file back and checks that every chosen outline
really is magenta; otherwise nothing is written. A green "✓ File saved" or red "File not saved"
banner confirms the result.

## Command line

```
CrunchCutContour [options] [file.eps | file.svg]
```

When running from source, replace `CrunchCutContour` with `python3 crunchcutcontour.py`.

| Option | Effect |
|---|---|
| *(no file)* | Editor: waits for a file to be dropped onto the page |
| `file.eps`, `file.svg` | Editor opened on that file |
| `--auto` | Direct conversion, without the editor: all pure magenta becomes CutContour |
| `--to-eps` | SVG: convert to EPS only, without a cut line (default: `<file>.eps`) |
| `--crop` | With `--auto` or `--to-eps`: crop the page to the artwork |
| `--crop-margin MM` | With `--crop`: margin around the artwork, in mm (default: 0) |
| `-o`, `--output FILE` | With `--auto`: output file (default: `<file>_CutContour.eps`) |
| `-f`, `--force` | With `--auto`: overwrite the output file if it exists |
| `--name NAME` | Spot color name (default: `CutContour`) |
| `--tolerance T` | Tolerance on each color component, from 0 to 1 (default: 0.002) |
| `--op-rgb NAME`, `--op-cmyk NAME` | With `--auto`: additional color operator to recognize (repeatable) |
| `--language en\|fr` | Interface language (default: the system language) |
| `--no-browser` | Editor: print the address without opening the browser |
| `--port PORT` | Editor: local port to use (default: random) |
| `--version` | Show the version |

The French option names are accepted too: `--sortie`, `--nom`, `--op-rvb`, `--op-cmjn`,
`--langue`, `--pas-de-navigateur`, `--recadrer`, `--marge`.

In `--auto` mode, if the file contains no pure magenta, nothing is written and the program
exits with code 1.

Examples:

```bash
CrunchCutContour --auto stickers.eps
```

```bash
CrunchCutContour --auto stickers.eps -o ready_to_cut.eps --force
```

```bash
CrunchCutContour --to-eps logo.svg
```

```bash
CrunchCutContour --auto logo.svg --crop --crop-margin 2
```

## Languages

The interface (command line, help, messages, editor pages) is available in **English** and
**French**. The language is chosen in this order:

1. the `--language` option (`--language fr`, `--language en`);
2. the system language (the `LANGUAGE`, `LC_ALL`, `LC_MESSAGES` and `LANG` variables, the
   Windows display language, the macOS preferred languages);
3. English, if the system language is not available.

In the editor, the language menu at the top right switches the language of the page and of the
messages; the current selection is kept.

## What the program changes in the file

The program only touches what it must; the rest of the file is copied byte for byte (line
endings, binary data and the TIFF/WMF preview of "DOS" EPS files included).

- **Cut color**: each affected color setting is replaced with a PostScript level 2 color space
  ```
  [/Separation /CutContour /DeviceCMYK {0 exch 0 0}] setcolorspace 1 setcolor
  ```
  that is, a `CutContour` spot color displayed as pure magenta.
- **Pure magenta recognized**: `1 0 1 setrgbcolor` and `0 1 0 0 setcmykcolor`, as well as their
  aliases defined in the file (for example `rg` in EPS files produced by cairo and Inkscape).
  Text, comments and image data are never modified.
- **Outline chosen in the editor**: the instruction that paints it is wrapped with a color
  setting inside `gsave … grestore`, which leaves the rest of the drawing unchanged.
- **Cropping**: the header boxes change (`%%BoundingBox`, `%%HiResBoundingBox`,
  `%%PageBoundingBox`, including an `(atend)` box in the trailer); embedded EPS files keep their
  own. The drawing is only modified if the frame cuts into it: it is then wrapped in
  `gsave … rectclip` / `grestore`.
- **Header**: the spot color is declared in the DSC comments (`%%DocumentCustomColors` and
  `%%CMYKCustomColor`), keeping any other spot colors already declared.

## SVG import

The program converts SVG to EPS (PostScript level 2) by itself, with no external software. Each
SVG shape becomes one EPS path, which can be selected on its own in the editor. A **pure
magenta** outline (`#ff00ff`, `magenta`, `fuchsia`) in the SVG becomes a cut line directly:
prepare it in Inkscape or Illustrator, then use `--auto`.

- **Supported**: `path` (all commands, arcs included), `rect` (rounded corners), `circle`,
  `ellipse`, `line`, `polyline`, `polygon`; groups, `use` and `symbol`, nested `svg`, `switch`;
  transforms; named colors, `#rgb`, `#rrggbb`, `rgb()`, `hsl()`, `currentColor`; fill (including
  the `evenodd` rule) and stroke (width, joins, caps, dashes); simple `<style>` sheets (type,
  `.class` and `#id` selectors, as in Illustrator exports); `viewBox`, `preserveAspectRatio` and
  units (`mm`, `cm`, `in`, `pt`, `px`…); `.svgz` files.
- **Approximated**: gradients and patterns become a flat color (the average of the gradient);
  transparency is simulated by blending the color with white.
- **Not converted** (a warning says so): text (convert it to paths before exporting), images,
  clipping paths and masks, filters, markers.
- The page size comes from the SVG's `width` and `height` (1 px = 0.75 pt), or failing that
  from its `viewBox`.
- For safety, SVG files that declare XML entities (`<!ENTITY …>`) are rejected.

## Limitations

- To display the file, the program runs the PostScript code itself with a simplified
  interpreter. "Simple" EPS files (Inkscape, cairo, most exports) are supported; some very
  complex Illustrator EPS files may only be partly displayed. A banner says so, and the paths
  shown can still be used.
- Text is not displayed: convert it to paths before exporting to see and select it.
- Images only appear as a grey frame and cannot be selected.
- A path painted by an instruction that paints several paths (a loop, for example) cannot be
  changed on its own.
- The editor needs a recent browser (Chrome, Firefox, Edge, Safari); Internet Explorer is not
  supported.
- The color space used requires a PostScript level 2 RIP or later (as do all current cutting
  software).

## Running from source

Python 3.8 or later is all you need; there are no dependencies.

```bash
python3 crunchcutcontour.py
```

The editor is a small local HTTP server: it only listens on `127.0.0.1`, on a random port, and
every request must carry a secret token generated at startup. It is therefore not reachable from
the network or from another web page. Under WSL, the page opens in the Windows browser.

### Tests

```bash
python3 -m unittest discover tests
```

### Adding a language

Texts are written in English in the code: `tr("…")` in Python, `t("…")` in JavaScript and
`[[…]]` in the HTML of the pages ([eps_editeur.py](eps_editeur.py)). The English text is the
translation key.

1. Copy [catalogue_fr.py](catalogue_fr.py) to `catalogue_xx.py` (`xx`: the ISO 639-1 code of
   the language, for example `de`) and translate each value. The `{names}` in braces are
   replaced by values: copy them unchanged.
2. Register the module in `LANGUES`, in [i18n.py](i18n.py).
3. Run the tests: they report any untranslated text, any translation that is no longer used
   and any missing `{…}` variable.

A new text in the code must be added to every catalog; the tests are there to remind you.

## Building the executables

The executables are built with [PyInstaller](https://pyinstaller.org) in the `dist/` folder.
PyInstaller does not cross-compile: each system is built on itself.

- **Windows**: on Windows, from the project folder
  ```bat
  construire_exe.bat win7
  construire_exe.bat win10
  ```
  Without an argument, it builds both. The script downloads the required Python from nuget.org
  into a subfolder (`python38`: 32-bit Python 3.8.10, `python313`: 64-bit Python 3.13) and
  installs PyInstaller there: nothing is installed on the system.
- **macOS and Linux**:
  ```bash
  sh construire.sh
  ```
  It uses `python3` (or the `PYTHON` variable), installs PyInstaller in `venv-build/`, and builds
  the executable for that Python's architecture, plus a `.zip` (macOS) or `.tar.gz` (Linux)
  archive. On Linux, the executable only runs on systems whose glibc is at least as recent as
  the build machine's.

### Publishing a release

The [.github/workflows/release.yml](.github/workflows/release.yml) workflow builds the five
files (Windows 7/8, Windows 10/11, Intel macOS, Apple Silicon macOS, Linux) on GitHub's
machines, with the same scripts.

1. Update `VERSION` in [crunchcutcontour.py](crunchcutcontour.py) and the text of
   [NOTES_DE_VERSION.md](NOTES_DE_VERSION.md), which describes the published version only;
   `{{VERSION}}` in it is replaced with the version number automatically.
2. Push the matching tag, for example:
   ```bash
   git tag v1.0.0 && git push origin v1.0.0
   ```

The workflow checks that the tag matches `VERSION`, then creates the GitHub release with the
files and the release notes. Run by hand (Actions tab), it only builds; the files are then in
the run's "artifacts".

## Code layout

| File | Role |
|---|---|
| [crunchcutcontour.py](crunchcutcontour.py) | Entry point and options; conversion of pure magenta to CutContour (`--auto`), DSC header, "DOS" EPS |
| [eps_editeur.py](eps_editeur.py) | Editor: local HTTP server, web pages (drop and editing), changes to the chosen outlines |
| [svg_eps.py](svg_eps.py) | SVG → EPS conversion |
| [eps_interpreteur.py](eps_interpreteur.py) | Simplified PostScript interpreter: runs the file and records each path, its color and the source instruction that painted it |
| [i18n.py](i18n.py) | Translation: language choice and detection, `tr()` function, translation of the argparse help |
| [catalogue_fr.py](catalogue_fr.py), [catalogue_en.py](catalogue_en.py) | Texts for each language |
| [tests/](tests) | Tests: complete translations, language detection, SVG conversion, cropping |
| [construire_exe.bat](construire_exe.bat) | Builds the Windows executables |
| [construire.sh](construire.sh) | Builds the macOS and Linux executables |
| [version_windows.py](version_windows.py) | Properties of the Windows executables (company, copyright, version) |
| [NOTES_DE_VERSION.md](NOTES_DE_VERSION.md) | Text of the GitHub release |
| [LICENSE](LICENSE) | GPL version 3 license |

## Author and license

Copyright © 2026 UTBM CrunchLab.

Author: Alexandre Willaume.

CrunchCutContour is free software: you can redistribute it and/or modify it under the terms of
the **GNU General Public License** as published by the Free Software Foundation, either version 3
of the License, or (at your option) any later version. It is distributed in the hope that it
will be useful, but **without any warranty**. The full license text is in [LICENSE](LICENSE).
