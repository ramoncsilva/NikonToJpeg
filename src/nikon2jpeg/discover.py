"""Find NEF files and compute their sibling-folder destinations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUFFIX = "_jpeg"


class DiscoverError(ValueError):
    pass


@dataclass(frozen=True)
class Job:
    src: Path
    dst: Path


def output_dir_for(input_dir: Path) -> Path:
    input_dir = input_dir.resolve()
    if not input_dir.name:
        raise DiscoverError(f"Cannot derive a sibling folder for drive root: {input_dir}")
    if input_dir.name.lower().endswith(SUFFIX):
        raise DiscoverError(f"Input folder already looks like an output folder: {input_dir}")
    return input_dir.with_name(input_dir.name + SUFFIX)


def _is_nef(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() == ".nef"


def plan(paths: list[Path], recursive: bool = False) -> list[Job]:
    """Turn input paths (folders and/or .nef files) into a de-duplicated job list."""
    jobs: dict[Path, Job] = {}
    for raw in paths:
        p = raw.resolve()
        if p.is_dir():
            out_root = output_dir_for(p)
            it = p.rglob("*") if recursive else p.iterdir()
            for f in sorted(it):
                if _is_nef(f):
                    dst = out_root / f.relative_to(p).with_suffix(".jpg")
                    jobs.setdefault(f, Job(f, dst))
        elif _is_nef(p):
            dst = output_dir_for(p.parent) / (p.stem + ".jpg")
            jobs.setdefault(p, Job(p, dst))
        else:
            raise DiscoverError(f"Not a folder or .nef file: {raw}")
    return list(jobs.values())
