# SDD Spec 001 — NikonToJpeg (NEF → JPEG converter)

| Field   | Value                                   |
|---------|-----------------------------------------|
| Status  | Draft (v2 — stack changed from Go to Python) |
| Owner   | ramoncsilva                             |
| Created | 2026-10-11                              |
| Stack   | Python ≥ 3.11, Windows 11 first-class   |

## 1. Goal

Convert all Nikon RAW (`.nef`) files in a folder to JPEG, writing the results to a **sibling folder**.
Output is tuned for posting on **Facebook and Instagram** (medium quality, sRGB, social-friendly size),
with **automatic dust-spot removal** and **noise reduction**.
The tool is reachable from the **Windows Explorer right-click menu**, both for a single image and for a folder.

### Non-goals (v1)

- Manual editing / retouching UI, cropping, color grading presets.
- Non-NEF RAW formats (CR2, ARW, DNG…). LibRaw supports them, so adding them later is trivial.
- macOS / Linux context-menu integration (CLI itself stays cross-platform).
- Uploading to social networks.

## 2. User stories

1. **Convert folder** — I right-click a folder → "Convert NEF to JPEG". A sibling folder `<folder>_jpeg` is created containing one `.jpg` per `.nef`.
2. **Convert image** — I right-click a `.nef` (or multi-select several) → "Convert to JPEG". The JPEG lands in the sibling folder `<parent>_jpeg`.
3. **CLI** — I run `nikon2jpeg convert <path>` from a terminal/script with the same behavior.
4. **Safe re-runs** — running twice does not duplicate or corrupt output; originals are never modified.

## 3. Functional requirements

| ID    | Requirement |
|-------|-------------|
| FR-1  | Input is a directory or one/more `.nef` files (case-insensitive extension). Directory scan is **non-recursive by default**; `--recursive` mirrors the subtree in the output. |
| FR-2  | Output folder is `<input_dir_name>_jpeg` located **next to** the input directory (sibling). For a single file, input dir = the file's parent. Created if missing. |
| FR-3  | Output file name = source base name + `.jpg` (`DSC_0001.NEF` → `DSC_0001.jpg`). Existing outputs are **skipped** unless `--overwrite`. |
| FR-4  | **Social preset (default):** sRGB, 8-bit, progressive JPEG, quality **82**, long edge capped at **2048 px** (never upscaled), 4:2:0 chroma subsampling. Aspect ratio preserved. |
| FR-5  | **Presets:** `facebook` (long edge 2048), `instagram` (long edge 1440, no crop, preserves 4:5 / 1:1 / 1.91:1 framing), `original` (no resize). Quality overridable with `--quality 1-100`. |
| FR-6  | **Noise reduction** enabled by default; strength `--denoise off|low|medium|high` (default `medium`). Chroma noise is reduced more aggressively than luma; edges and fine texture preserved. |
| FR-7  | **Dust-spot removal** enabled by default (`--dust on|off`, plus `--dust-sensitivity low|medium|high`). Detect small, roughly round, low-contrast dark blobs (typical sensor dust) and inpaint them from surrounding pixels. Must not remove genuine small details (stars, catchlights, birds, text) — see NFR-4. |
| FR-8  | **EXIF:** orientation applied to pixels (tag reset to 1), capture date, camera/lens and exposure info preserved; **GPS stripped** by default (`--keep-gps` to retain). |
| FR-9  | **Parallelism:** process files concurrently with a process pool, default workers = `max(1, cpu_count // 2)`, `--jobs N` to override. |
| FR-10 | **Progress & report:** per-file status line (rich/tqdm progress bar), final summary (converted / skipped / failed, elapsed time). Exit code 0 = all ok, 1 = some failed, 2 = bad usage. |
| FR-11 | **Failure isolation:** a corrupt/unsupported NEF is logged and skipped; the batch continues. Partial output files are never left behind (write to temp file + `os.replace`). |
| FR-12 | **Context menu install/uninstall** via `nikon2jpeg install` / `nikon2jpeg uninstall` (no admin rights; per-user registry through `winreg`). See §6. |
| FR-13 | `--dry-run` lists what would be converted without writing. |
| FR-14 | Optional `config.toml` (`%APPDATA%\NikonToJpeg\config.toml`, read with `tomllib`) supplies default flags; CLI flags win. Context-menu invocations use the config. |

## 4. Non-functional requirements

| ID     | Requirement |
|--------|-------------|
| NFR-1  | Original `.nef` files are opened **read-only** and never modified or moved. |
| NFR-2  | Throughput target: ≤ 6 s per 24 MP image on a 4-core laptop with default settings. |
| NFR-3  | Memory: ≤ ~1.2 GB per worker peak for 45 MP files (float/16-bit buffers); default worker count keeps total bounded. |
| NFR-4  | Dust false-positive guard: spots only touched if diameter < 0.4 % of image width, contrast below a threshold, and not in high-frequency/edge regions. `--save-dust-mask` (debug) writes the detection mask next to the output. |
| NFR-5  | Distribution: pip-installable package **and** a single-folder/one-file Windows `.exe` built with PyInstaller (bundles LibRaw via `rawpy` wheels; no Python install required for context-menu use). |
| NFR-6  | Windows paths: long paths, spaces and non-ASCII characters (e.g. `Férias`) must work in CLI and context menu (use `pathlib`, UTF-8 safe quoting). |
| NFR-7  | Deterministic output: same input + flags → byte-identical JPEG (pin library versions in lockfile). |
| NFR-8  | Code quality: type hints, `ruff` + `mypy` clean, `pytest` coverage ≥ 80 % on non-I/O logic. |

## 5. Design

### 5.1 Libraries

| Concern | Library | Why |
|---------|---------|-----|
| NEF decode | **`rawpy`** (LibRaw binding, binary wheels for Windows) | True RAW: demosaic, white balance, 16-bit sRGB output. No native build needed. |
| Array ops | `numpy` | Pipeline buffers. |
| Denoise, dust, resize | **`opencv-python-headless`** | `fastNlMeansDenoisingColored`, `medianBlur`, `connectedComponentsWithStats`, `inpaint` (Telea), `resize` (INTER_AREA / LANCZOS4). |
| JPEG encode + ICC | **`Pillow`** | `quality`, `progressive`, `subsampling`, `icc_profile`, `optimize`. |
| EXIF | `piexif` (or Pillow's `Exif`) | Read from NEF/preview, strip GPS, write into JPEG. |
| Preview fallback | `rawpy.extract_thumb()` | Fast mode / fallback when full decode fails. |
| CLI | `typer` (or `argparse`) | Subcommands `convert`, `install`, `uninstall`, `version`. |
| Progress | `rich` | Progress bar + summary table. |
| Windows menu | stdlib `winreg` | Per-user registry keys. |
| Single-instance batching | `msvcrt`/named mutex via `ctypes` + local socket or named pipe | See §6. |
| Packaging | `PyInstaller`, `pyproject.toml` (hatchling), `uv` for env/lock | |

### 5.2 Decoding strategy

- **Default:** `rawpy.imread(path).postprocess(use_camera_wb=True, output_bps=16, output_color=rawpy.ColorSpace.sRGB, no_auto_bright=False, half_size=<True if target long edge ≤ half of sensor long edge>)`. `half_size` skips demosaicing interpolation — big speed-up when we downscale to 2048 anyway, and slightly reduces noise.
- **`--fast`:** use embedded JPEG preview via `extract_thumb()` (no dust/denoise gain, but near-instant). Auto-fallback to this if full decode raises.
- Orientation: `postprocess` applies `user_flip` from RAW metadata by default; verify in tests (AC-11).

### 5.3 Processing pipeline

```
discover → decode(rawpy, 16-bit) → dust removal → denoise → resize → light sharpen → 8-bit sRGB → encode JPEG (+EXIF/ICC) → atomic write
```

- **Order rationale:** dust and denoise run at the highest available resolution, where spots and noise are most separable from detail; resize (INTER_AREA) averages residual noise; a light unsharp mask restores crispness lost to denoise/resize.
- **Dust removal:**
  1. Luma channel; background estimate with a large-kernel median (≈ 2–3× max spot size).
  2. Residual = background − luma; threshold by sensitivity → candidate mask.
  3. `connectedComponentsWithStats`; keep blobs passing size, circularity (≥ 0.6) and local-edge-density tests.
  4. Dilate mask by 2 px; `cv2.inpaint(..., INPAINT_TELEA)`.
- **Denoise:** convert to YCrCb; luma `fastNlMeansDenoising` (h by level), chroma channels stronger `h` or bilateral; levels map to `h` values tuned on high-ISO samples.
- **Color:** `rawpy` output is already sRGB; embed the bundled sRGB ICC profile (`ImageCms.createProfile("sRGB")`) in output.
- **Encode:** Pillow `save(..., quality=82, progressive=True, optimize=True, subsampling="4:2:0", icc_profile=..., exif=...)`.

### 5.4 Project layout

```
NikonToJpeg/
├── pyproject.toml
├── uv.lock
├── src/nikon2jpeg/
│   ├── __init__.py
│   ├── __main__.py            # python -m nikon2jpeg
│   ├── cli.py                 # typer app
│   ├── config.py              # config.toml + presets (dataclasses)
│   ├── discover.py            # scan, sibling-output path logic
│   ├── decode.py              # rawpy wrapper, preview fallback
│   ├── dust.py                # detection + inpainting
│   ├── denoise.py
│   ├── encode.py              # resize, sharpen, ICC, EXIF, JPEG write
│   ├── pipeline.py            # per-file orchestration + ProcessPool
│   ├── report.py              # progress + summary
│   └── shellmenu.py           # winreg install/uninstall + batch collector (Windows only)
├── tests/
│   ├── data/                  # small sample NEFs + golden outputs
│   └── test_*.py
├── packaging/nikon2jpeg.spec  # PyInstaller
├── specs/001-nef-to-jpeg/spec.md
└── README.md
```

### 5.5 Output path rules

| Invocation | Input dir | Output dir |
|------------|-----------|------------|
| Folder `D:\Photos\Trip` | `D:\Photos\Trip` | `D:\Photos\Trip_jpeg` |
| File `D:\Photos\Trip\DSC_1.NEF` | `D:\Photos\Trip` | `D:\Photos\Trip_jpeg` |
| Recursive, subfolder `Day2` | `…\Trip\Day2` | `…\Trip_jpeg\Day2` |

If the input folder is itself named `*_jpeg`, abort with a clear message (prevents `_jpeg_jpeg` loops).

## 6. Windows context menu (FR-12)

Per-user registry entries under `HKCU\Software\Classes` (no admin), written with `winreg`:

| Target | Key | Menu label | Command |
|--------|-----|-----------|---------|
| Folder | `Directory\shell\NikonToJpeg` | **Convert NEF to JPEG** | `"<exe>" convert "%1"` |
| Folder background | `Directory\Background\shell\NikonToJpeg` | **Convert NEF to JPEG (this folder)** | `"<exe>" convert "%V"` |
| `.nef` file | `SystemFileAssociations\.nef\shell\NikonToJpeg` | **Convert to JPEG** | `"<exe>" convert "%1"` |

`<exe>` is the PyInstaller `nikon2jpeg.exe` when frozen (`sys.frozen`), otherwise `pythonw`/`python -m nikon2jpeg` resolved to an absolute path.

Notes:
- Multi-select on files: Windows launches one process per file. The exe uses a **named mutex + local socket** so the first instance becomes the leader, collects paths for ~500 ms from followers, then processes them as one batch (one window).
- **Windows 11** shows classic verbs under **"Show more options"** (Shift+F10). A native top-level entry needs an `IExplorerCommand` handler + sparse MSIX package — **out of scope for v1** (stretch).
- Menu launches a console window with the progress bar; on completion it shows the summary and pauses 3 s unless `--no-pause`.
- `uninstall` removes exactly the keys it created; `install` is idempotent and records the exe path (re-run after moving it).

## 7. CLI reference (v1)

```
nikon2jpeg convert <path>... [flags]
nikon2jpeg install | uninstall
nikon2jpeg version

Flags:
  --preset facebook|instagram|original   (default facebook)
  --quality 1-100                        (default 82)
  --max-edge N                           override preset long edge
  --denoise off|low|medium|high          (default medium)
  --dust on|off                          (default on)
  --dust-sensitivity low|medium|high     (default medium)
  --recursive
  --overwrite
  --keep-gps
  --fast                                 use embedded preview instead of full RAW decode
  --jobs N
  --dry-run
  --save-dust-mask
  --no-pause
```

## 8. Acceptance criteria

| # | Scenario | Expected |
|---|----------|----------|
| AC-1 | Folder with 10 `.nef`, run `convert` on it | `<folder>_jpeg` has 10 `.jpg`; exit 0; originals unchanged (hash equal) |
| AC-2 | Re-run same command | 10 skipped, 0 converted, files untouched; `--overwrite` regenerates |
| AC-3 | Default output of a 6000×4000 NEF | JPEG long edge = 2048, ratio preserved, quality ≈ 82, sRGB ICC embedded, size 300 KB–1.5 MB typical |
| AC-4 | Image with visible dust spots on sky | Spots absent in output; `--save-dust-mask` shows them detected; stars/birds in control image preserved |
| AC-5 | High-ISO (≥ 6400) shot | Visibly lower chroma/luma noise vs. `--denoise off`, fine texture still legible |
| AC-6 | Corrupt `.nef` among valid ones | That file reported failed; others converted; exit 1; no partial `.jpg` left |
| AC-7 | Right-click folder → "Convert NEF to JPEG" | Console shows progress; sibling folder created; works with `D:\Fotos\Férias 2026` |
| AC-8 | Right-click one `.nef` | Single JPEG in `<parent>_jpeg` |
| AC-9 | Select 20 `.nef` → right-click | One batch run (one window), 20 outputs |
| AC-10 | `uninstall` | All registry keys removed; menu entries gone |
| AC-11 | Portrait-orientation NEF | JPEG displays upright in Windows Photos and Instagram |
| AC-12 | GPS-tagged NEF | Output has no GPS tags unless `--keep-gps` |
| AC-13 | PyInstaller build on a clean Windows VM without Python | `nikon2jpeg.exe convert` and the context menu work |

## 9. Milestones / task breakdown

1. **M1 – Skeleton & discovery:** `pyproject.toml`/uv, CLI, sibling-path logic, process pool, atomic writes, tests for FR-1/2/3/11.
2. **M2 – Decode:** `rawpy` wrapper, `half_size` heuristic, preview fallback, orientation + EXIF read. Tests with fixture NEFs.
3. **M3 – Encode:** resize, sharpen, sRGB ICC, quality 82 progressive JPEG, EXIF write, GPS strip, presets.
4. **M4 – Denoise:** YCrCb NLM levels, benchmark vs NFR-2.
5. **M5 – Dust removal:** detection, filtering, inpainting, mask debug output; tune on sample images (AC-4).
6. **M6 – Windows integration:** `install`/`uninstall`, single-instance batch collector, console summary (AC-7…10).
7. **M7 – Packaging & docs:** PyInstaller spec, README, GitHub Actions (ruff, mypy, pytest, build windows exe) (AC-13).
8. **Stretch:** Windows 11 top-level menu, toast progress, dust map reuse across a shoot, other RAW formats, GUI wrapper.

## 10. Risks & open questions

| # | Item | Notes / proposed default |
|---|------|--------------------------|
| 1 | PyInstaller exe size (OpenCV + numpy ≈ 100–150 MB) and slow cold start (~1–2 s) for the context menu | Use `opencv-python-headless`, one-folder build, UPX off; acceptable for v1. |
| 2 | Full RAW decode is slower than the embedded preview | `half_size` + process pool; `--fast` available. |
| 3 | Dust detection quality is heuristic | Conservative default; mask debug flag. Candidate v2: reuse a dust map across frames of the same shoot (sensor spots repeat). |
| 4 | Windows 11 hides classic menu items | Documented; stretch goal for native menu. |
| 5 | "Medium quality" interpreted as JPEG q=82 | Confirm; Instagram re-compresses anyway, so 80–85 is the sweet spot. |
| 6 | LibRaw's default tone/contrast differs from Nikon's in-camera "look" | Option to prefer embedded preview (`--fast`) or add a gentle tone curve; revisit after sample review. |
| 7 | New-model NEFs (e.g. high-efficiency compressed Z-series files) need a recent LibRaw | Pin a recent `rawpy` and document minimum version. |
