"""Per-file conversion and the batch runner."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

import cv2

from nikon2jpeg import decode, denoise, dust, encode
from nikon2jpeg.config import Settings
from nikon2jpeg.discover import Job


@dataclass
class Result:
    job: Job
    status: str  # "converted" | "skipped" | "failed"
    detail: str = ""


def convert_one(job: Job, s: Settings) -> Result:
    if job.dst.exists() and not s.overwrite:
        return Result(job, "skipped", "output exists")
    try:
        cv2.setNumThreads(1)  # parallelism comes from the process pool
        d = decode.decode(job.src, s.target_edge, s.fast)
        rgb = d.rgb
        if s.dust:
            rgb, mask = dust.remove_dust(rgb, s.dust_sensitivity)
            if s.save_dust_mask:
                job.dst.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(job.dst.with_suffix(".dustmask.png")), mask)
        rgb = denoise.denoise(rgb, s.denoise)
        rgb = encode.sharpen(encode.resize(rgb, s.target_edge))
        encode.write_jpeg(rgb, job.dst, s.quality, encode.filter_exif(d.exif, s.keep_gps))
        return Result(job, "converted")
    except Exception as exc:  # noqa: BLE001 - isolate failures per file (FR-11)
        return Result(job, "failed", f"{type(exc).__name__}: {exc}")


def run(
    jobs: list[Job],
    settings: Settings,
    on_result: Callable[[Result], None] | None = None,
) -> tuple[list[Result], float]:
    start = time.perf_counter()
    results: list[Result] = []

    def emit(r: Result) -> None:
        results.append(r)
        if on_result:
            on_result(r)

    workers = min(settings.workers, len(jobs)) if jobs else 1
    if workers <= 1:
        for j in jobs:
            emit(convert_one(j, settings))
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(convert_one, j, settings) for j in jobs]
            for f in as_completed(futures):
                emit(f.result())
    return results, time.perf_counter() - start
