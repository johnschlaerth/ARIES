"""Configuration and scenario loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Entity, Scenario
from .scenario_generator import generate_scenario_payload, should_generate_scenario, write_generated_scenario
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
    return load_or_generate_scenario(config)


def load_or_generate_scenario(
    config: dict[str, Any],
    scenario_path: str | Path | None = None,
    force_random: bool = False,
    seed: int | None = None,
) -> Scenario:
    """Load a fixed scenario or generate one according to config/CLI intent."""

    if scenario_path and not force_random:
        return load_scenario(scenario_path, config)
    if should_generate_scenario(config, force_random=force_random):
        payload = generate_scenario_payload(config, seed=seed)
        if config.get("scenario_generation", {}).get("write_generated_scenario", True):
            write_generated_scenario(payload, config)
        return Scenario(
            scenario_name=payload["scenario_name"],
            description=payload["description"],
            map=payload["map"],
            friendly_entities=[Entity.from_dict(e) for e in payload["friendly_entities"]],
            enemy_entities=[Entity.from_dict(e) for e in payload["enemy_entities"]],
            neutral_entities=[Entity.from_dict(e) for e in payload["neutral_entities"]],
            image_assignments=payload.get("image_assignments", []),
        )
    return load_scenario(scenario_path or config["paths"]["scenario_file"], config)
