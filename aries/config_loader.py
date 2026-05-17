"""Configuration and scenario loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Entity, Scenario
from .utils import load_dotenv_if_present, load_json, project_root


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load the JSON config and normalize relative paths to project root."""

    root = project_root()
    load_dotenv_if_present(root)
    path = Path(config_path) if config_path else root / "config" / "aries_config.json"
    config = load_json(path)
    config["_root"] = str(root)
    return config


def resolve_project_path(config: dict[str, Any], value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(config.get("_root", project_root())) / path


def load_scenario(path: str | Path, config: dict[str, Any] | None = None) -> Scenario:
    """Load a scenario JSON file and apply entity defaults."""

    if config is None:
        config = load_config()
    scenario_path = resolve_project_path(config, path)
    payload = load_json(scenario_path)
    for key in ["scenario_name", "description", "map"]:
        if key not in payload:
            raise ValueError(f"Scenario missing required field: {key}")
    map_payload = payload["map"]
    for key in ["width", "height", "terrain_seed", "objective_position", "friendly_base_position"]:
        if key not in map_payload:
            raise ValueError(f"Scenario map missing required field: {key}")

    return Scenario(
        scenario_name=payload["scenario_name"],
        description=payload["description"],
        map=map_payload,
        friendly_entities=[Entity.from_dict(e) for e in payload.get("friendly_entities", [])],
        enemy_entities=[Entity.from_dict(e) for e in payload.get("enemy_entities", [])],
        neutral_entities=[Entity.from_dict(e) for e in payload.get("neutral_entities", [])],
        image_assignments=payload.get("image_assignments", []),
    )


def load_default_scenario(config: dict[str, Any] | None = None) -> Scenario:
    if config is None:
        config = load_config()
    return load_scenario(config["paths"]["scenario_file"], config)
