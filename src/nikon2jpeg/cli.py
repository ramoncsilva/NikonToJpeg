"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from nikon2jpeg import __version__, pipeline
from nikon2jpeg.config import (
    DENOISE_LEVELS,
    PRESET_MAX_EDGE,
    SENSITIVITIES,
    Settings,
    apply_overrides,
    load_config_defaults,
)
from nikon2jpeg.discover import DiscoverError, plan


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nikon2jpeg", description="Nikon NEF -> JPEG for social media")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="convert folders and/or .nef files")
    c.add_argument("paths", nargs="+", type=Path)
    c.add_argument("--preset", choices=PRESET_MAX_EDGE)
    c.add_argument("--quality", type=int, choices=range(1, 101), metavar="1-100")
    c.add_argument("--max-edge", type=int)
    c.add_argument("--denoise", choices=DENOISE_LEVELS)
    c.add_argument("--dust", choices=["on", "off"])
    c.add_argument("--dust-sensitivity", choices=SENSITIVITIES)
    c.add_argument("--recursive", action="store_true", default=None)
    c.add_argument("--overwrite", action="store_true", default=None)
    c.add_argument("--keep-gps", action="store_true", default=None)
    c.add_argument("--fast", action="store_true", default=None, help="use embedded preview")
    c.add_argument("--jobs", type=int)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--save-dust-mask", action="store_true", default=None)
    c.add_argument("--pause", action="store_true", help="wait before closing (context menu)")

    sub.add_parser("install", help="add Explorer right-click entries")
    sub.add_parser("uninstall", help="remove Explorer right-click entries")
    sub.add_parser("version")
    return p


def _settings(args: argparse.Namespace) -> Settings:
    overrides = {
        "preset": args.preset,
        "quality": args.quality,
        "max_edge": args.max_edge,
        "denoise": args.denoise,
        "dust": None if args.dust is None else args.dust == "on",
        "dust_sensitivity": args.dust_sensitivity,
        "recursive": args.recursive,
        "overwrite": args.overwrite,
        "keep_gps": args.keep_gps,
        "fast": args.fast,
        "jobs": args.jobs,
        "save_dust_mask": args.save_dust_mask,
    }
    base = apply_overrides(Settings(), load_config_defaults())
    return apply_overrides(base, overrides)


def _convert(args: argparse.Namespace) -> int:
    settings = _settings(args)
    try:
        jobs = plan(args.paths, settings.recursive)
    except DiscoverError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not jobs:
        print("No .nef files found.")
        return 0

    if args.dry_run:
        for j in jobs:
            print(f"{j.src} -> {j.dst}")
        print(f"{len(jobs)} file(s) would be processed.")
        return 0

    total = len(jobs)
    done = 0

    def on_result(r: pipeline.Result) -> None:
        nonlocal done
        done += 1
        extra = f" ({r.detail})" if r.detail else ""
        print(f"[{done}/{total}] {r.status:9} {r.job.src.name}{extra}", flush=True)

    results, elapsed = pipeline.run(jobs, settings, on_result)
    counts = {s: sum(r.status == s for r in results) for s in ("converted", "skipped", "failed")}
    print(
        f"\nDone in {elapsed:.1f}s: {counts['converted']} converted, "
        f"{counts['skipped']} skipped, {counts['failed']} failed."
    )
    if args.pause:
        time.sleep(3)
    return 1 if counts["failed"] else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "convert":
        return _convert(args)
    if args.cmd == "version":
        print(__version__)
        return 0
    from nikon2jpeg import shellmenu

    if args.cmd == "install":
        shellmenu.install()
        print("Context menu installed.")
    else:
        shellmenu.uninstall()
        print("Context menu removed.")
    return 0
