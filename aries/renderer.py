"""Pygame renderer for the retro tactical display."""

from __future__ import annotations

from pathlib import Path

from .models import Entity


class Renderer:
    def __init__(self, config: dict, sim) -> None:
        import pygame

        self.pygame = pygame
        self.config = config
        self.sim = sim
        display = config["display"]
        self.width = int(display["width"])
        self.height = int(display["height"])
        self.map_width = int(sim.scenario.map["width"])
        self.map_height = int(sim.scenario.map["height"])
        self.panel_width = 360
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("ARIES MVP Tactical Simulation")
        self.font = pygame.font.SysFont("courier", 15)
        self.small = pygame.font.SysFont("courier", 13)
        # Contours are static for a scenario, so compute them once instead of
        # scanning the elevation array every rendered frame.
        generation = config.get("scenario_generation", {})
        self.terrain_contours = sim.terrain.contour_points(
            sim.scenario.map.get("contour_count", generation.get("contour_count", 18)),
            stride=int(generation.get("contour_dot_stride", 1)),
        )
        self.colors = {
            "black": (0, 0, 0),
            "green": (0, 220, 80),
            "dim_green": (0, 75, 35),
            "red": (240, 40, 40),
            "blue": (60, 120, 255),
            "cyan": (0, 220, 230),
            "yellow": (245, 220, 60),
            "white": (230, 230, 230),
            "gray": (110, 110, 110),
        }

    def scale(self, point: list[float]) -> tuple[int, int]:
        map_draw_width = self.width - self.panel_width - 20
        map_draw_height = self.height - 170
        return (
            int(point[0] / self.map_width * map_draw_width) + 10,
            int(point[1] / self.map_height * map_draw_height) + 40,
        )

    def draw_text(self, text: str, pos: tuple[int, int], color="green", font=None) -> None:
        surf = (font or self.font).render(text, True, self.colors[color])
        self.screen.blit(surf, pos)

    def render(self, controls) -> None:
        pygame = self.pygame
        self.screen.fill(self.colors["black"])
        self._draw_terrain()
        self._draw_map_markers()
        if controls.show_paths:
            for entity in self.sim.all_entities:
                self._draw_path(entity)
        self._draw_network()
        if self.config.get("display", {}).get("show_effect_ranges", True):
            for entity in self.sim.friendlies:
                self._draw_effect_range(entity)
        for entity in self.sim.all_entities:
            self._draw_entity(entity, controls.show_vectors)
        self._draw_panels()
        pygame.display.flip()

    def _draw_terrain(self) -> None:
        pygame = self.pygame
        for contour in self.terrain_contours:
            for point in contour:
                pygame.draw.circle(self.screen, self.colors["dim_green"], self.scale(point), 1)

    def _draw_map_markers(self) -> None:
        pygame = self.pygame
        objective = self.scale(self.sim.scenario.map["objective_position"])
        base = self.scale(self.sim.scenario.map["friendly_base_position"])
        pygame.draw.line(self.screen, self.colors["yellow"], (objective[0] - 8, objective[1]), (objective[0] + 8, objective[1]), 2)
        pygame.draw.line(self.screen, self.colors["yellow"], (objective[0], objective[1] - 8), (objective[0], objective[1] + 8), 2)
        pygame.draw.circle(self.screen, self.colors["blue"], base, 9, 2)
        self.draw_text("OBJ", (objective[0] + 10, objective[1] - 8), "yellow", self.small)
        self.draw_text("BASE", (base[0] + 10, base[1] - 8), "blue", self.small)

    def _draw_path(self, entity: Entity) -> None:
        pygame = self.pygame
        if len(entity.path) < 2 or not entity.active:
            return
        color = self.colors["cyan"] if entity.allegiance == "friendly" else self.colors["red"]
        pts = [self.scale(p) for p in entity.path]
        for a, b in zip(pts, pts[1:]):
            # Dotted paths: draw short alternating line segments.
            for i in range(0, 20, 4):
                t1 = i / 20
                t2 = min(1.0, (i + 2) / 20)
                p1 = (int(a[0] + (b[0] - a[0]) * t1), int(a[1] + (b[1] - a[1]) * t1))
                p2 = (int(a[0] + (b[0] - a[0]) * t2), int(a[1] + (b[1] - a[1]) * t2))
                pygame.draw.line(self.screen, color, p1, p2, 1)

    def _draw_network(self) -> None:
        pygame = self.pygame
        comms = [f for f in self.sim.friendlies if f.active and f.payload_type == "comms"]
        for node in comms:
            pos = self.scale(node.position)
            radius = int(node.network_radius / self.map_width * (self.width - self.panel_width - 20))
            pygame.draw.circle(self.screen, self.colors["blue"], pos, radius, 1)
            for friendly in self.sim.friendlies:
                if friendly.network_supported and friendly.id != node.id:
                    pygame.draw.line(self.screen, self.colors["blue"], pos, self.scale(friendly.position), 1)

    def _draw_effect_range(self, entity: Entity) -> None:
        if not entity.active or entity.effect_range <= 0 or entity.payload_type == "comms":
            return
        radius = int(entity.effect_range / self.map_width * (self.width - self.panel_width - 20))
        color = self.colors["cyan"] if entity.payload_type in {"ew", "isr"} else self.colors["yellow"] if entity.payload_type == "cuas" else self.colors["green"]
        self.pygame.draw.circle(self.screen, color, self.scale(entity.position), radius, 1)

    def _draw_entity(self, entity: Entity, show_vector: bool) -> None:
        pygame = self.pygame
        x, y = self.scale(entity.position)
        color = self._entity_color(entity)
        if not entity.active:
            color = self.colors["red"] if entity.allegiance == "enemy" else self.colors["gray"]
            pygame.draw.line(self.screen, color, (x - 8, y - 8), (x + 8, y + 8), 3)
            pygame.draw.line(self.screen, color, (x + 8, y - 8), (x - 8, y + 8), 3)
            return
        if entity.entity_type == "enemy_drone":
            pygame.draw.polygon(self.screen, color, [(x, y + 10), (x - 9, y - 7), (x + 9, y - 7)], 2)
        elif entity.entity_type in {"enemy_ground_vehicle", "enemy_unknown", "unknown_contact"}:
            pygame.draw.polygon(self.screen, color, [(x, y - 9), (x + 9, y), (x, y + 9), (x - 9, y)], 2)
            if "unknown" in entity.entity_type:
                self.draw_text("?", (x - 4, y - 9), "red", self.small)
        elif entity.entity_type == "enemy_ew" or entity.payload_type == "ew":
            pygame.draw.circle(self.screen, color, (x, y), 9, 2)
            pygame.draw.circle(self.screen, color, (x, y), 17, 1)
        elif entity.payload_type == "cuas":
            pygame.draw.rect(self.screen, color, (x - 8, y - 8, 16, 16), 2)
            pygame.draw.polygon(self.screen, color, [(x, y - 11), (x - 6, y + 2), (x + 6, y + 2)], 2)
        elif entity.payload_type == "effect":
            pygame.draw.rect(self.screen, color, (x - 8, y - 8, 16, 16), 2)
            pygame.draw.line(self.screen, color, (x - 6, y), (x + 6, y), 2)
            pygame.draw.line(self.screen, color, (x, y - 6), (x, y + 6), 2)
        elif entity.payload_type == "isr":
            pygame.draw.circle(self.screen, color, (x, y), 8, 2)
            pygame.draw.arc(self.screen, color, (x - 15, y - 8, 30, 16), 0, 3.14, 1)
        elif entity.payload_type == "comms":
            pygame.draw.circle(self.screen, color, (x, y), 8, 2)
            pygame.draw.circle(self.screen, color, (x, y), 14, 1)
        else:
            pygame.draw.circle(self.screen, color, (x, y), 6, 1)
        if show_vector and entity.velocity != [0.0, 0.0]:
            pygame.draw.line(self.screen, self.colors["white"], (x, y), (int(x + entity.velocity[0] * 2), int(y + entity.velocity[1] * 2)), 1)
        # Show health bar under damaged friendlies
        if entity.allegiance == "friendly" and entity.health < 100:
            bar_w = 22
            filled = max(1, int(bar_w * entity.health / 100))
            bar_color = (230, 80, 30) if entity.health < 35 else (220, 160, 30) if entity.health < 65 else (0, 200, 60)
            pygame.draw.rect(self.screen, (40, 40, 40), (x - bar_w // 2, y + 10, bar_w, 4))
            pygame.draw.rect(self.screen, bar_color, (x - bar_w // 2, y + 10, filled, 4))
        label = entity.id if entity.health >= 100 or entity.allegiance != "friendly" else f"{entity.id} {int(entity.health)}%"
        self.draw_text(label, (x + 10, y - 7), "white", self.small)

    def _entity_color(self, entity: Entity) -> tuple[int, int, int]:
        if entity.allegiance == "enemy":
            return self.colors["red"]
        if entity.allegiance == "neutral":
            return self.colors["white"]
        # Friendly units shift toward orange/red as health drops
        if entity.health < 35:
            return (230, 80, 30)   # critical — orange-red
        if entity.health < 65:
            return (220, 160, 30)  # damaged — amber
        if entity.payload_type == "comms":
            return self.colors["blue"]
        if entity.payload_type == "ew":
            return self.colors["cyan"]
        if entity.payload_type == "cuas":
            return self.colors["yellow"]
        return self.colors["green"]

    def _draw_panels(self) -> None:
        x = self.width - self.panel_width + 10
        active_enemies = sum(1 for enemy in self.sim.enemies if enemy.active)
        objective_status = "SECURE" if self.sim.state.outcome != "OBJECTIVE_REACHED_BY_ENEMY" else "REACHED"
        self.draw_text(f"ARIES MVP  STEP {self.sim.state.step}", (10, 10), "green")
        self.draw_text(f"MODE {self.config.get('run_mode', 'mock')}  OUTCOME {self.sim.state.outcome}", (310, 10), "cyan")
        self.draw_text(self.sim.scenario.scenario_name[:34], (690, 10), "white", self.small)
        self.draw_text(f"FRIENDLY {len(self.sim.friendlies)}  ENEMY ACTIVE {active_enemies}  OBJ {objective_status}", (10, 28), "white", self.small)
        self.draw_text("PRIORITY TOP 5", (x, 20), "yellow")
        y = 45
        for target in self.sim.manager.priority_table[:5]:
            self.draw_text(f"{target.id:7} {target.priority_score_global:5.1f} T{target.threat_level}", (x, y), "red", self.small)
            y += 18
        y += 10
        self.draw_text("ASSIGNMENTS", (x, y), "yellow")
        y += 22
        for friendly in self.sim.friendlies:
            status = "CONNECTED" if friendly.network_supported else "LOCAL"
            self.draw_text(f"{friendly.id:7} -> {friendly.target_id or '-':7} {status}", (x, y), "cyan", self.small)
            y += 18
        y += 10
        self.draw_text("LEGEND", (x, y), "yellow")
        y += 22
        for line in ["RED enemy", "BLUE comms", "CYAN ew", "GREEN isr/effect", "YELLOW c-uas", "X disabled"]:
            self.draw_text(line, (x, y), "white", self.small)
            y += 17
        y += 6
        self.draw_text("B: builder / classifier", (x, y), "gray", self.small)
        y = self.height - 155
        self.draw_text("EVENT LOG", (10, y), "yellow")
        y += 20
        for event in self.sim.state.events[-7:]:
            self.draw_text(f"[{event.step}] {event.message}"[:120], (10, y), "green", self.small)
            y += 18

    def save_screenshot(self) -> Path:
        out_dir = Path(self.config["_root"]) / "outputs"
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"screenshot_step_{self.sim.state.step}.png"
        self.pygame.image.save(self.screen, str(path))
        return path
