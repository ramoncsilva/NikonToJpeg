"""Per-file conversion and the batch runner."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from concurrent.futures import Executor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from nikon2jpeg import decode, denoise, dust, dustmap, encode
from nikon2jpeg.config import Settings
from nikon2jpeg.discover import Job

ShootMaps = dict[int, np.ndarray]


@dataclass
class Result:
    job: Job
    status: str  # "converted" | "skipped" | "failed"
    detail: str = ""


def convert_one(job: Job, s: Settings, shoot_maps: ShootMaps | None = None) -> Result:
    if job.dst.exists() and not s.overwrite:
        return Result(job, "skipped", "output exists")
    try:
        cv2.setNumThreads(1)  # parallelism comes from the process pool
        d = decode.decode(job.src, s.target_edge, s.fast)
        rgb = d.rgb
        if s.dust:
            shoot_map = (shoot_maps or {}).get(d.flip)
            rgb, mask = dust.remove_dust(rgb, s.dust_sensitivity, shoot_map)
            if s.save_dust_mask:
                job.dst.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(job.dst.with_suffix(".dustmask.png")), mask)
        rgb = denoise.denoise(rgb, s.denoise)
        rgb = encode.sharpen(encode.resize(rgb, s.target_edge))
        encode.write_jpeg(rgb, job.dst, s.quality, encode.filter_exif(d.exif, s.keep_gps))
        return Result(job, "converted")
    except Exception as exc:  # noqa: BLE001 - isolate failures per file (FR-11)
        return Result(job, "failed", f"{type(exc).__name__}: {exc}")


def _map_unordered(executor: Executor | None, fn: Callable[..., Any], items: list[tuple]) -> Iterator:
    if executor is None:
        for args in items:
            yield fn(*args)
        return
    for fut in as_completed([executor.submit(fn, *args) for args in items]):
        yield fut.result()


def learn_shoot_maps(
    jobs: list[Job], s: Settings, executor: Executor | None
) -> tuple[ShootMaps, int]:
    """Phase 1: find dust spots that recur across frames. Returns (maps, frames used)."""
    cands = [
        c
        for c in _map_unordered(
            executor, dustmap.candidate, [(j.src, s.dust_sensitivity) for j in jobs]
        )
        if c is not None
    ]
    return dustmap.consensus(cands), len(cands)


def run(
    jobs: list[Job],
    settings: Settings,
    on_result: Callable[[Result], None] | None = None,
    info: Callable[[str], None] | None = None,
) -> tuple[list[Result], float]:
    start = time.perf_counter()
    results: list[Result] = []
    todo = [j for j in jobs if settings.overwrite or not j.dst.exists()]
    workers = min(settings.workers, len(jobs)) if jobs else 1
    executor = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
    try:
        shoot_maps: ShootMaps = {}
        learn = settings.dust and settings.dust_map and not settings.fast
        if learn and len(todo) >= dustmap.MIN_IMAGES:
            if info:
                info(f"Learning recurring dust spots from {len(todo)} previews...")
            shoot_maps, used = learn_shoot_maps(todo, settings, executor)
            if info:
                spots = sum(cv2.connectedComponents(m)[0] - 1 for m in shoot_maps.values())
                info(
                    f"Shoot dust map: {spots} recurring spot(s) from {used} frame(s)."
                    if shoot_maps
                    else "Shoot dust map: no recurring spots found."
                )

        for r in _map_unordered(executor, convert_one, [(j, settings, shoot_maps) for j in jobs]):
            results.append(r)
            if on_result:
                on_result(r)
    finally:
        if executor:
            executor.shutdown()
    return results, time.perf_counter() - start
