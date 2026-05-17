"""Small utility functions shared across modules."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any


def distance(a: list[float] | tuple[float, float], b: list[float] | tuple[float, float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def unit_vector(a: list[float], b: list[float]) -> list[float]:
    dx = float(b[0]) - float(a[0])
    dy = float(b[1]) - float(a[1])
    mag = math.hypot(dx, dy)
    if mag == 0:
        return [0.0, 0.0]
    return [dx / mag, dy / mag]


def move_toward(position: list[float], goal: list[float], max_distance: float) -> tuple[list[float], list[float]]:
    """Move toward a goal and return new position plus velocity vector."""

    direction = unit_vector(position, goal)
    step = min(max_distance, distance(position, goal))
    return [position[0] + direction[0] * step, position[1] + direction[1] * step], [direction[0] * step, direction[1] * step]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dotenv_if_present(root: Path | None = None) -> list[Path]:
    """Load simple KEY=VALUE pairs from local .env files.

    The loader intentionally supports only the common assignment format because
    the MVP should not depend on python-dotenv just to pick up an API key. Values
    already present in the shell environment win over file values.
    """

    root = root or project_root()
    candidates = [root / ".env", root.parent / ".env"]
    loaded: list[Path] = []
    for path in candidates:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        loaded.append(path)
    return loaded
