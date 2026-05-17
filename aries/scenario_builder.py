"""Simple Pygame scenario builder.

This is intentionally minimal: it supports placing common entity types and
saving a JSON scenario. The main MVP does not depend on it.
"""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((1000, 700))
    font = pygame.font.SysFont("courier", 16)
    selected = "friendly_comms"
    entities = []
    mapping = {
        pygame.K_1: ("friendly", "ground", "friendly_comms", "comms"),
        pygame.K_2: ("friendly", "ground", "friendly_ew", "ew"),
        pygame.K_3: ("friendly", "ground", "friendly_isr", "isr"),
        pygame.K_4: ("friendly", "ground", "friendly_cuas", "cuas"),
        pygame.K_5: ("friendly", "ground", "friendly_effect", "effect"),
        pygame.K_6: ("enemy", "air", "enemy_drone", "none"),
        pygame.K_7: ("enemy", "ground", "enemy_ground_vehicle", "none"),
        pygame.K_8: ("enemy", "ground", "enemy_ew", "none"),
        pygame.K_9: ("unknown", "ground", "unknown_contact", "none"),
        pygame.K_0: ("neutral", "non_threat", "non_threat_object", "none"),
    }
    selected_tuple = mapping[pygame.K_1]
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in mapping:
                    selected_tuple = mapping[event.key]
                    selected = selected_tuple[2]
                elif event.key == pygame.K_s:
                    _save_builder_scenario(entities)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                allegiance, domain, entity_type, payload = selected_tuple
                entities.append({
                    "id": f"b{len(entities)+1}",
                    "name": selected,
                    "allegiance": allegiance,
                    "domain": domain,
                    "entity_type": entity_type,
                    "payload_type": payload,
                    "position": [event.pos[0], event.pos[1]],
                    "speed": 18 if allegiance == "friendly" else 14,
                    "threat_level": 7 if allegiance == "enemy" else 1,
                })
        screen.fill((0, 0, 0))
        screen.blit(font.render(f"Selected {selected} | 1-0 choose | click place | S save | ESC quit", True, (0, 220, 80)), (10, 10))
        for entity in entities:
            color = (240, 40, 40) if entity["allegiance"] == "enemy" else (0, 220, 80)
            pygame.draw.circle(screen, color, entity["position"], 6, 1)
        pygame.display.flip()
    pygame.quit()


def _save_builder_scenario(entities: list[dict]) -> None:
    root = Path(__file__).resolve().parents[1]
    payload = {
        "scenario_name": "Builder Scenario",
        "description": "Scenario created with the basic ARIES builder.",
        "map": {
            "width": 1000,
            "height": 700,
            "terrain_seed": 321,
            "contour_count": 12,
            "objective_position": [850, 350],
            "friendly_base_position": [100, 350],
        },
        "friendly_entities": [e for e in entities if e["allegiance"] == "friendly"],
        "enemy_entities": [e for e in entities if e["allegiance"] in {"enemy", "unknown"}],
        "neutral_entities": [e for e in entities if e["allegiance"] == "neutral"],
        "image_assignments": [],
    }
    path = root / "scenarios" / "builder_scenario.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
