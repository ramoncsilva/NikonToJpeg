"""Settings, presets and optional config.toml defaults."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, fields, replace
from pathlib import Path

PRESET_MAX_EDGE: dict[str, int | None] = {
    "facebook": 2048,
    "instagram": 1440,
    "original": None,
}
DENOISE_LEVELS = ("off", "low", "medium", "high")
SENSITIVITIES = ("low", "medium", "high")


@dataclass(frozen=True)
class Settings:
    preset: str = "facebook"
    quality: int = 82
    max_edge: int | None = None  # overrides the preset when set
    denoise: str = "medium"
    dust: bool = True
    dust_sensitivity: str = "medium"
    dust_map: bool = True  # learn recurring sensor-dust spots across the batch
    recursive: bool = False
    overwrite: bool = False
    keep_gps: bool = False
    fast: bool = False
    jobs: int = 0  # 0 = auto
    save_dust_mask: bool = False

    @property
    def target_edge(self) -> int | None:
        return self.max_edge if self.max_edge else PRESET_MAX_EDGE[self.preset]

    @property
    def workers(self) -> int:
        return self.jobs if self.jobs > 0 else max(1, (os.cpu_count() or 2) // 2)


def config_path() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "NikonToJpeg" / "config.toml"


def load_config_defaults(path: Path | None = None) -> dict[str, object]:
    """Read config.toml; unknown keys are ignored."""
    path = path or config_path()
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    known = {f.name for f in fields(Settings)}
    return {k: v for k, v in data.items() if k in known}


def apply_overrides(base: Settings, overrides: dict[str, object]) -> Settings:
    return replace(base, **{k: v for k, v in overrides.items() if v is not None})
