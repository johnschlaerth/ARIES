"""Local vehicle-level target selection and path intent."""

from __future__ import annotations

import math

from .models import Entity
from .pathfinding import astar_path, direct_path
from .scoring import is_targetable, local_priority_score
from .terrain import Terrain


class LocalAgent:
    """Decision helper for one friendly node."""

    def __init__(self, map_width: int, map_height: int):
        self.map_diag = math.hypot(map_width, map_height)

    def choose_target(
        self,
        friendly: Entity,
        enemies: list[Entity],
        terrain: Terrain,
        central_target_id: str | None,
    ) -> Entity | None:
        if not friendly.active or friendly.payload_type == "comms":
            friendly.target_id = None
            return None
        best: Entity | None = None
        best_score = 0.0
        for target in enemies:
            if not is_targetable(target):
                continue
            accessibility = terrain_accessibility(friendly, target, terrain)
            score = local_priority_score(friendly, target, central_target_id, self.map_diag, accessibility)
            if score > best_score:
                best = target
                best_score = score
        friendly.target_id = best.id if best else None
        friendly.priority_score_local = best_score
        friendly.status_text = f"TGT {friendly.target_id}" if best else "NO TARGET"
        return best

    def update_path(self, friendly: Entity, target: Entity | None, terrain: Terrain, support_point: list[float]) -> None:
        if not friendly.active:
            return
        if friendly.payload_type == "comms":
            goal = support_point
        elif target:
            goal = target.position
        else:
            goal = friendly.position
        friendly.path = astar_path(friendly.position, goal, terrain) if friendly.domain == "ground" else direct_path(friendly.position, goal)


def terrain_accessibility(friendly: Entity, target: Entity, terrain: Terrain) -> float:
    """Cheap local accessibility estimate used during target scoring.

    Full A* is reserved for the selected target path. Running A* for every
    friendly-target pair every timestep made the demo do avoidable work. This
    estimate samples local terrain and still down-ranks targets sitting behind
    expensive terrain without turning scoring into path planning.
    """

    if friendly.domain != "ground":
        return 1.0
    sample_cost = (terrain.cost_at(friendly.position) + terrain.cost_at(target.position)) / 2.0
    return max(0.15, min(1.0, 1.0 / sample_cost))
