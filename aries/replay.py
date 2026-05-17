"""Replay persistence helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config_loader import resolve_project_path
from .simulation import Simulation
from .utils import load_json, write_json


def save_replay(sim: Simulation, config: dict) -> Path:
    replay_dir = resolve_project_path(config, config["paths"]["replay_folder"])
    replay_dir.mkdir(parents=True, exist_ok=True)
    path = replay_dir / f"replay_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_json(path, {"scenario_name": sim.scenario.scenario_name, "frames": sim.state.replay_frames})
    return path


def load_replay(path: str | Path) -> dict:
    return load_json(Path(path))
