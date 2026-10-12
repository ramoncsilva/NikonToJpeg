# NikonToJpeg

Convert Nikon `.nef` RAW files to JPEGs ready for Facebook / Instagram (sRGB, quality 82, long edge 2048 px), with automatic dust-spot removal and noise reduction. Results go to a sibling folder: `Trip` → `Trip_jpeg`.

Spec: [specs/001-nef-to-jpeg/spec.md](specs/001-nef-to-jpeg/spec.md)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

## Usage

```powershell
nikon2jpeg convert D:\Photos\Trip                 # whole folder -> D:\Photos\Trip_jpeg
nikon2jpeg convert D:\Photos\Trip\DSC_0001.NEF    # one image
nikon2jpeg convert D:\Photos\Trip --preset instagram --denoise high --dry-run
nikon2jpeg install      # add Explorer right-click entries (per user, no admin)
nikon2jpeg uninstall
```

Run `nikon2jpeg convert --help` for all flags. Defaults can be set in `%APPDATA%\NikonToJpeg\config.toml`
(keys match the flag names, e.g. `quality = 85`, `denoise = "low"`).

On Windows 11 the entries appear under **Show more options** (Shift+F10).

## Development

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check src tests
```

## Windows right-click menu

`nikon2jpeg install` adds the entries (per user, no admin). Selecting several files in Explorer opens a single window for the whole batch.
Windows 11 hides classic entries behind **Show more options**; `nikon2jpeg classic-menu on` (undo with `off`) makes Explorer show the classic menu directly. Restart Explorer afterwards.

## Dust removal

Each image is checked for small, round, dark spots on clean areas. With three or more files, spots that recur at the same position across the shoot (sensor dust) are also learned from the embedded previews and repaired in every frame. Disable with `--dust-map off`, or all dust handling with `--dust off`. `--save-dust-mask` writes the mask next to each JPEG.

## Standalone .exe

```powershell
.venv\Scripts\pip install -e ".[dev]"
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
packaging\build.ps1                      # -> dist\nikon2jpeg\nikon2jpeg.exe
dist\nikon2jpeg\nikon2jpeg.exe install   # menu now points at the exe
```

Run `install` again if you move the folder.

## Status

Spec milestones M1-M7 are implemented; CI builds the exe on Windows. Not done: a native top-level Windows 11 menu entry (needs a signed MSIX + COM DLL), and dust/noise thresholds are tuned on one sample photo.
