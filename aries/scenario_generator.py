"""Random-but-sensible scenario generation for ARIES."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from .models import Entity, Scenario
from .utils import write_json


FRIENDLY_TEMPLATES = [
    ("COMMS", "ARIES-COMMS Relay", "friendly_comms", "comms", 13, 0, 1.0, None, 230),
    ("EW", "ARIES-EW", "friendly_ew", "ew", 24, 140, 1.0, None, 180),
    ("ISR", "ARIES-ISR", "friendly_isr", "isr", 24, 180, 1.0, None, 180),
    ("CUAS", "ARIES-CUAS", "friendly_cuas", "cuas", 30, 150, 0.9, 8, 180),
    ("EFFECT", "ARIES-EFFECT", "friendly_effect", "effect", 26, 120, 0.85, 8, 180),
]


def should_generate_scenario(config: dict[str, Any], force_random: bool = False) -> bool:
    generation = config.get("scenario_generation", {})
    return force_random or bool(generation.get("enabled", False))


def generate_scenario(config: dict[str, Any], seed: int | None = None) -> Scenario:
    """Generate a scenario with friendlies left and threats right."""

    payload = generate_scenario_payload(config, seed)
    return Scenario(
        scenario_name=payload["scenario_name"],
        description=payload["description"],
        map=payload["map"],
        friendly_entities=[Entity.from_dict(e) for e in payload["friendly_entities"]],
        enemy_entities=[Entity.from_dict(e) for e in payload["enemy_entities"]],
        neutral_entities=[Entity.from_dict(e) for e in payload["neutral_entities"]],
        image_assignments=payload.get("image_assignments", []),
    )


def generate_scenario_payload(config: dict[str, Any], seed: int | None = None) -> dict[str, Any]:
    generation = config.get("scenario_generation", {})
    sim_cfg = config.get("simulation", {})
    configured_seed = generation.get("seed")
    if seed is None:
        seed = configured_seed if configured_seed is not None else random.SystemRandom().randint(1, 2_000_000_000)
    rng = random.Random(int(seed))

    width = int(generation.get("map_width", 1000))
    height = int(generation.get("map_height", 700))
    max_enemies = int(generation.get("max_enemies", 8))
    min_enemies = int(generation.get("min_enemies", 5))
    max_neutrals = int(generation.get("max_neutrals", 2))
    min_enemies = max(1, min(min_enemies, max_enemies))

    objective = [int(width * 0.74), int(height * 0.50 + rng.uniform(-height * 0.05, height * 0.05))]
    base = [int(width * 0.10), int(height * 0.50 + rng.uniform(-height * 0.06, height * 0.06))]

    enemy_count = rng.randint(min_enemies, max_enemies)
    drone_count = min(enemy_count, rng.randint(2, min(3, enemy_count)))
    include_ew = enemy_count >= 5
    include_unknown = enemy_count >= 6
    ground_count = enemy_count - drone_count - (1 if include_ew else 0) - (1 if include_unknown else 0)
    ground_count = max(1, ground_count)

    payload = {
        "scenario_name": f"Generated ARIES Scenario {seed}",
        "description": "Randomized but side-separated ARIES scenario generated from config.",
        "map": {
            "width": width,
            "height": height,
            "terrain_seed": int(sim_cfg.get("seed", 42)) if generation.get("terrain_seed") is None else int(generation["terrain_seed"]),
            "contour_count": int(generation.get("contour_count", 18)),
            "objective_position": objective,
            "friendly_base_position": base,
        },
        "friendly_entities": _friendly_entities(rng, width, height, base),
        "enemy_entities": [],
        "neutral_entities": [],
        "image_assignments": [],
    }

    for i in range(drone_count):
        payload["enemy_entities"].append(_enemy(rng, i + 1, "enemy_drone", "air", width, height, speed=rng.uniform(3.5, 5.2), threat=rng.randint(6, 9)))
    for i in range(ground_count):
        payload["enemy_entities"].append(_enemy(rng, i + 1, "enemy_ground_vehicle", "ground", width, height, speed=rng.uniform(2.6, 3.8), threat=rng.randint(5, 8)))
    if include_ew:
        payload["enemy_entities"].append(_enemy(rng, 1, "enemy_ew", "ground", width, height, speed=rng.uniform(1.0, 2.0), threat=9))
    if include_unknown:
        payload["enemy_entities"].append(_enemy(rng, 1, "unknown_contact", "ground", width, height, speed=rng.uniform(1.8, 2.8), threat=4, allegiance="unknown", confidence=0.35))

    for i in range(rng.randint(1, max_neutrals)):
        payload["neutral_entities"].append({
            "id": f"NEUT{i + 1}",
            "name": "Neutral Marker",
            "allegiance": "neutral",
            "domain": "non_threat",
            "entity_type": "non_threat_object",
            "position": [round(rng.uniform(width * 0.42, width * 0.58), 1), round(rng.uniform(height * 0.12, height * 0.88), 1)],
            "speed": 0,
            "threat_level": 1,
            "confidence": 0.95,
        })

    _assign_existing_images(payload, config)
    return payload


def write_generated_scenario(payload: dict[str, Any], config: dict[str, Any]) -> Path:
    root = Path(config["_root"])
    out_path = root / config.get("scenario_generation", {}).get("generated_scenario_file", "scenarios/generated_latest.json")
    write_json(out_path, payload)
    return out_path


def _friendly_entities(rng: random.Random, width: int, height: int, base: list[int]) -> list[dict[str, Any]]:
    entities = []
    offsets = [(-18, -90), (24, -45), (28, 45), (58, -125), (62, 125)]
    for idx, template in enumerate(FRIENDLY_TEMPLATES):
        prefix, name, entity_type, payload, speed, effect_range, probability, magazine, network_radius = template
        dx, dy = offsets[idx]
        entities.append({
            "id": f"{prefix}1",
            "name": name,
            "allegiance": "friendly",
            "domain": "ground",
            "entity_type": entity_type,
            "payload_type": payload,
            "position": [
                round(_bounded(base[0] + dx + rng.uniform(-18, 18), width * 0.04, width * 0.30), 1),
                round(_bounded(base[1] + dy + rng.uniform(-20, 20), height * 0.08, height * 0.92), 1),
            ],
            "speed": speed,
            "effect_range": effect_range,
            "effect_probability": probability,
            "effect_cooldown_steps": 3 if payload == "cuas" else 4,
            "magazine": magazine,
            "network_radius": network_radius,
            "sensor_radius": 230 if payload == "isr" else 160,
            "threat_level": 1,
        })
    return entities


def _enemy(
    rng: random.Random,
    number: int,
    entity_type: str,
    domain: str,
    width: int,
    height: int,
    speed: float,
    threat: int,
    allegiance: str = "enemy",
    confidence: float | None = None,
) -> dict[str, Any]:
    labels = {
        "enemy_drone": "Enemy Drone",
        "enemy_ground_vehicle": "Enemy Ground Vehicle",
        "enemy_ew": "Enemy EW Node",
        "unknown_contact": "Unknown Contact",
    }
    prefix = {
        "enemy_drone": "DRONE",
        "enemy_ground_vehicle": "GROUND",
        "enemy_ew": "EWE",
        "unknown_contact": "UNK",
    }[entity_type]
    return {
        "id": f"{prefix}{number}",
        "name": f"{labels[entity_type]} {number}",
        "allegiance": allegiance,
        "domain": domain,
        "entity_type": entity_type,
        "position": [round(rng.uniform(width * 0.90, width * 0.98), 1), round(rng.uniform(height * 0.08, height * 0.92), 1)],
        "speed": round(speed, 2),
        "threat_level": threat,
        "confidence": confidence if confidence is not None else round(rng.uniform(0.78, 0.94), 2),
        "effect_range": 180 if entity_type == "enemy_ew" else 80,
    }


def _assign_existing_images(payload: dict[str, Any], config: dict[str, Any]) -> None:
    image_folder = Path(config["_root"]) / config["paths"].get("image_folder", "data/images")
    if not image_folder.exists():
        return
    images = sorted(p for p in image_folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    max_assignments = min(len(images), len(payload["enemy_entities"]), int(config.get("scenario_generation", {}).get("max_image_assignments", 3)))
    for entity, image in zip(payload["enemy_entities"][:max_assignments], images[:max_assignments]):
        payload["image_assignments"].append({"entity_id": entity["id"], "image_path": str(image.relative_to(Path(config["_root"])))})


def _bounded(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
