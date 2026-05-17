"""Pygame scenario setup tool for ARIES."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config_loader import load_config, load_scenario
from .scenario_generator import generate_scenario_payload


ENTITY_CHOICES = {
    "1": ("friendly", "ground", "friendly_comms", "comms", 13, 1),
    "2": ("friendly", "ground", "friendly_ew", "ew", 24, 1),
    "3": ("friendly", "ground", "friendly_isr", "isr", 24, 1),
    "4": ("friendly", "ground", "friendly_cuas", "cuas", 30, 1),
    "5": ("friendly", "ground", "friendly_effect", "effect", 26, 1),
    "6": ("enemy", "air", "enemy_drone", "none", 4.5, 8),
    "7": ("enemy", "ground", "enemy_ground_vehicle", "none", 3.2, 7),
    "8": ("enemy", "ground", "enemy_ew", "none", 1.5, 9),
    "9": ("unknown", "ground", "unknown_contact", "none", 2.5, 4),
    "0": ("neutral", "non_threat", "non_threat_object", "none", 0, 1),
}


def main() -> None:
    import pygame

    config = load_config()
    width = int(config.get("scenario_generation", {}).get("map_width", 1000))
    height = int(config.get("scenario_generation", {}).get("map_height", 700))
    screen = pygame.display.set_mode((width + 360, height))
    pygame.display.set_caption("ARIES Scenario Builder")
    pygame.init()
    font = pygame.font.SysFont("courier", 16)
    small = pygame.font.SysFont("courier", 13)

    selected_key = "1"
    entities: list[dict[str, Any]] = []
    selected_entity: dict[str, Any] | None = None
    drag_offset = [0.0, 0.0]
    status = "R random | S save | L load | C clear | drag to move"
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif key_name in ENTITY_CHOICES:
                    selected_key = key_name
                    status = f"Selected {ENTITY_CHOICES[selected_key][2]}"
                elif event.key == pygame.K_r:
                    payload = generate_scenario_payload(config)
                    entities = payload["friendly_entities"] + payload["enemy_entities"] + payload["neutral_entities"]
                    status = f"Generated random setup with {len(entities)} entities"
                elif event.key == pygame.K_s:
                    path = save_builder_scenario(entities, config)
                    status = f"Saved {path.name}"
                elif event.key == pygame.K_l:
                    entities = load_builder_entities(config)
                    status = f"Loaded {len(entities)} entities"
                elif event.key == pygame.K_c:
                    entities = []
                    status = "Cleared"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] <= width:
                    selected_entity = find_entity_at(entities, event.pos)
                    if selected_entity:
                        drag_offset = [selected_entity["position"][0] - event.pos[0], selected_entity["position"][1] - event.pos[1]]
                    else:
                        entities.append(make_entity(selected_key, event.pos, entities))
                        status = f"Placed {ENTITY_CHOICES[selected_key][2]}"
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                selected_entity = None
            elif event.type == pygame.MOUSEMOTION and selected_entity:
                selected_entity["position"] = [
                    round(max(0, min(width, event.pos[0] + drag_offset[0])), 1),
                    round(max(0, min(height, event.pos[1] + drag_offset[1])), 1),
                ]

        draw_builder(screen, font, small, config, entities, selected_key, status)
        pygame.display.flip()
    pygame.quit()


def make_entity(selected_key: str, position: tuple[int, int], existing: list[dict[str, Any]]) -> dict[str, Any]:
    allegiance, domain, entity_type, payload, speed, threat = ENTITY_CHOICES[selected_key]
    prefix = {
        "friendly_comms": "COMMS",
        "friendly_ew": "EW",
        "friendly_isr": "ISR",
        "friendly_cuas": "CUAS",
        "friendly_effect": "EFFECT",
        "enemy_drone": "DRONE",
        "enemy_ground_vehicle": "GROUND",
        "enemy_ew": "EWE",
        "unknown_contact": "UNK",
        "non_threat_object": "NEUT",
    }[entity_type]
    number = 1 + sum(1 for entity in existing if entity["id"].startswith(prefix))
    return {
        "id": f"{prefix}{number}",
        "name": entity_type.replace("_", " ").title(),
        "allegiance": allegiance,
        "domain": domain,
        "entity_type": entity_type,
        "payload_type": payload,
        "position": [float(position[0]), float(position[1])],
        "speed": speed,
        "threat_level": threat,
        "confidence": 0.9 if allegiance != "unknown" else 0.35,
        "effect_range": 150 if payload == "cuas" else 180 if payload in {"ew", "isr"} else 120 if payload == "effect" else 80,
        "effect_probability": 0.9 if payload == "cuas" else 0.85 if payload == "effect" else 1.0,
        "magazine": 8 if payload in {"cuas", "effect"} else None,
    }


def build_scenario_payload(entities: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    generation = config.get("scenario_generation", {})
    width = int(generation.get("map_width", 1000))
    height = int(generation.get("map_height", 700))
    return {
        "scenario_name": "Builder Scenario",
        "description": "Scenario created with the ARIES GUI scenario builder.",
        "map": {
            "width": width,
            "height": height,
            "terrain_seed": int(config.get("simulation", {}).get("seed", 42)),
            "contour_count": int(generation.get("contour_count", 18)),
            "objective_position": [int(width * 0.84), int(height * 0.5)],
            "friendly_base_position": [int(width * 0.10), int(height * 0.5)],
        },
        "friendly_entities": [e for e in entities if e["allegiance"] == "friendly"],
        "enemy_entities": [e for e in entities if e["allegiance"] in {"enemy", "unknown"}],
        "neutral_entities": [e for e in entities if e["allegiance"] == "neutral"],
        "image_assignments": [],
    }


def save_builder_scenario(entities: list[dict[str, Any]], config: dict[str, Any]) -> Path:
    root = Path(config["_root"])
    path = root / "scenarios" / "builder_scenario.json"
    path.write_text(json.dumps(build_scenario_payload(entities, config), indent=2), encoding="utf-8")
    return path


def load_builder_entities(config: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(config["_root"]) / "scenarios" / "builder_scenario.json"
    if not path.exists():
        return []
    scenario = load_scenario(path, config)
    return [e.to_dict() for e in scenario.all_entities]


def find_entity_at(entities: list[dict[str, Any]], pos: tuple[int, int]) -> dict[str, Any] | None:
    for entity in reversed(entities):
        x, y = entity["position"]
        if (x - pos[0]) ** 2 + (y - pos[1]) ** 2 <= 16**2:
            return entity
    return None


def draw_builder(screen, font, small, config: dict[str, Any], entities: list[dict[str, Any]], selected_key: str, status: str) -> None:
    import pygame

    width = int(config.get("scenario_generation", {}).get("map_width", 1000))
    height = int(config.get("scenario_generation", {}).get("map_height", 700))
    screen.fill((0, 0, 0))
    pygame.draw.line(screen, (0, 80, 40), (width * 0.32, 0), (width * 0.32, height), 1)
    pygame.draw.line(screen, (90, 20, 20), (width * 0.70, 0), (width * 0.70, height), 1)
    screen.blit(font.render("FRIENDLY SIDE", True, (0, 180, 120)), (20, 16))
    screen.blit(font.render("ENEMY SIDE", True, (220, 50, 50)), (int(width * 0.74), 16))
    for entity in entities:
        x, y = [int(v) for v in entity["position"]]
        color = color_for(entity)
        pygame.draw.circle(screen, color, (x, y), 8, 2)
        screen.blit(small.render(entity["id"], True, color), (x + 10, y - 8))

    panel_x = width + 12
    screen.blit(font.render("ARIES BUILDER", True, (0, 220, 80)), (panel_x, 16))
    screen.blit(small.render(status[:42], True, (240, 220, 80)), (panel_x, 44))
    y = 76
    for key, choice in ENTITY_CHOICES.items():
        marker = ">" if key == selected_key else " "
        line = f"{marker}{key} {choice[2]}"
        screen.blit(small.render(line, True, color_for_choice(choice)), (panel_x, y))
        y += 18
    y += 14
    for line in ["Mouse click: place", "Drag marker: move", "R: random sensible setup", "S: save builder_scenario", "L: load builder_scenario", "C: clear", "ESC: quit"]:
        screen.blit(small.render(line, True, (220, 220, 220)), (panel_x, y))
        y += 18


def color_for(entity: dict[str, Any]) -> tuple[int, int, int]:
    if entity["allegiance"] in {"enemy", "unknown"}:
        return (240, 40, 40)
    if entity["allegiance"] == "neutral":
        return (180, 180, 180)
    if entity["payload_type"] == "comms":
        return (60, 120, 255)
    if entity["payload_type"] == "ew":
        return (0, 220, 230)
    if entity["payload_type"] == "cuas":
        return (245, 220, 60)
    return (0, 220, 80)


def color_for_choice(choice: tuple) -> tuple[int, int, int]:
    return color_for({"allegiance": choice[0], "payload_type": choice[3]})


if __name__ == "__main__":
    main()
