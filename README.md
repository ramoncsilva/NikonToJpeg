# NikonToJpeg

Convert Nikon `.nef` RAW files to JPEGs ready for Facebook / Instagram (sRGB, quality 82, long edge 2048 px), with automatic dust-spot removal and noise reduction. Results go to a sibling folder: `Trip` → `Trip_jpeg`.

Spec: [specs/001-nef-to-jpeg/spec.md](specs/001-nef-to-jpeg/spec.md)

## Installation

Windows 10/11. Pick one of the two options; the standalone `.exe` is the better choice for everyday use because it does not depend on a Python environment.

### Option A — Standalone `.exe` (recommended)

1. **Get the app.** Either build it once (needs Python 3.11+):

   ```powershell
   git clone git@github.com:ramoncsilva/NikonToJpeg.git
   cd NikonToJpeg
   python -m venv .venv
   .venv\Scripts\pip install -e ".[dev]"
   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
   ```

   …or download the `nikon2jpeg-windows` artifact from the latest GitHub Actions run and unzip it.
   The build produces the folder `dist\nikon2jpeg\` (about 180 MB; `nikon2jpeg.exe` plus its libraries — keep the files together).

2. **Put it somewhere permanent.** The right-click menu stores the path to the `.exe`, so do not leave it in a folder you will move or delete:

   ```powershell
   robocopy dist\nikon2jpeg "$env:LOCALAPPDATA\Programs\NikonToJpeg" /MIR
   ```

   (`robocopy` exit codes below 8 mean success. Re-run the same command to update later.)

3. **Add the right-click menu** (current user only, no admin rights needed):

   ```powershell
   & "$env:LOCALAPPDATA\Programs\NikonToJpeg\nikon2jpeg.exe" install
   ```

4. **Optional — use it from any terminal** by adding the folder to your user `PATH`, then open a new terminal:

   ```powershell
   [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:LOCALAPPDATA\Programs\NikonToJpeg", "User")
   ```

### Option B — From source (development)

```powershell
git clone git@github.com:ramoncsilva/NikonToJpeg.git
cd NikonToJpeg
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\nikon2jpeg install      # optional: right-click menu
```

With this option the menu runs `.venv\Scripts\python.exe -m nikon2jpeg`, so it keeps working only while the project folder and its `.venv` stay where they are.

### Check the installation

```powershell
nikon2jpeg version
nikon2jpeg convert D:\Photos\Trip --dry-run     # lists what would be converted, writes nothing
```

Then right-click a folder with `.nef` files in Explorer. On Windows 11 the entries are under **Show more options** (or Shift + right-click); see [Windows right-click menu](#windows-right-click-menu) to show them directly.

### Update

Pull the changes, rebuild (Option A, steps 1–2) or just `git pull` (Option B). If the `.exe` location changed, run `install` again so the menu points at the new path.

### Uninstall

```powershell
nikon2jpeg uninstall           # removes the right-click entries
nikon2jpeg classic-menu off    # only if you turned it on
```

Then delete the app folder and, if you created it, `%APPDATA%\NikonToJpeg\config.toml`. Your photos and the `_jpeg` output folders are never touched.

## Usage

```powershell
nikon2jpeg convert D:\Photos\Trip                 # whole folder -> D:\Photos\Trip_jpeg
nikon2jpeg convert D:\Photos\Trip\DSC_0001.NEF    # one image
nikon2jpeg convert D:\Photos\Trip --preset instagram --denoise high --dry-run
```

Run `nikon2jpeg convert --help` for all flags. Defaults can be set in `%APPDATA%\NikonToJpeg\config.toml`
(keys match the flag names, e.g. `quality = 85`, `denoise = "low"`).

Original `.nef` files are never modified, and files already converted are skipped unless you pass `--overwrite`.

## Windows right-click menu

`nikon2jpeg install` adds three entries for the current user:

| Right-click on | Entry |
|---|---|
| a folder | **Convert NEF to JPEG** |
| the background of an open folder | **Convert NEF to JPEG (this folder)** |
| one or more `.nef` files | **Convert to JPEG** |

Selecting several files opens a single window for the whole batch. Windows itself hides classic entries when more than about 15 files are selected; use the folder entry for bigger sets.

Windows 11 hides classic entries behind **Show more options**. `nikon2jpeg classic-menu on` (undo with `off`) makes Explorer show the classic menu directly for everything, not just this tool; restart Explorer or sign out afterwards.

## Dust removal

Each image is checked for small, round, dark spots on clean areas. With three or more files, spots that recur at the same position across the shoot (sensor dust) are also learned from the embedded previews and repaired in every frame. Disable with `--dust-map off`, or all dust handling with `--dust off`. `--save-dust-mask` writes the mask next to each JPEG.

## Troubleshooting

| Symptom | Fix |
|---|---|
| No entries in the right-click menu | On Windows 11 look under **Show more options**; run `nikon2jpeg install` again. |
| Menu stopped working after moving the app | Run `install` from the new location. |
| `build.ps1` says scripts are disabled | Run it as `powershell -ExecutionPolicy Bypass -File packaging\build.ps1`. |
| `nikon2jpeg` is not recognized | Use the full path to the `.exe`, or add its folder to `PATH` (step 4). |

## Development

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check src tests
```

## Status

Spec milestones M1-M7 are implemented; CI builds the exe on Windows. Not done: a native top-level Windows 11 menu entry (needs a signed MSIX + COM DLL), and dust/noise thresholds are tuned on one sample photo.
