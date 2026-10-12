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

## Status

Spec milestones M1–M5 are implemented; M6 is partly done (install/uninstall work, but selecting several files still opens one window per file). M7 (PyInstaller packaging) is pending. No real NEF fixtures are checked in yet, so the RAW decode path has only been exercised through unit tests of the imaging stages.
