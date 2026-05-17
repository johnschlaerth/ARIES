"""Central battle-manager scoring and assignment."""

from __future__ import annotations

import math

from .models import Entity
from .scoring import global_priority_score, is_targetable, payload_match


class BattleManager:
    """Computes global threat ranking and central friendly recommendations."""

    def __init__(self, objective_position: list[float], map_width: int, map_height: int):
        self.objective_position = objective_position
        self.map_diag = math.hypot(map_width, map_height)
        self.priority_table: list[Entity] = []
        self.assignments: dict[str, str] = {}

    def update(self, friendlies: list[Entity], enemies: list[Entity]) -> dict[str, str]:
        targets = [enemy for enemy in enemies if is_targetable(enemy)]
        for target in targets:
            target.priority_score_global = global_priority_score(target, friendlies, self.objective_position, self.map_diag)
        self.priority_table = sorted(targets, key=lambda e: e.priority_score_global, reverse=True)

        assignments: dict[str, str] = {}
        claimed: set[str] = set()
        for friendly in [f for f in friendlies if f.active and f.payload_type != "comms"]:
            best = None
            best_score = 0.0
            for target in self.priority_table:
                score = target.priority_score_global + payload_match(friendly.payload_type, target) * 30.0
                if target.id in claimed:
                    score *= 0.8
                if score > best_score:
                    best = target
                    best_score = score
            if best:
                assignments[friendly.id] = best.id
                claimed.add(best.id)
        self.assignments = assignments
        return assignments

