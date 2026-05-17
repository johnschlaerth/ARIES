"""Scoring helpers for global and local decision logic."""

from __future__ import annotations

from .models import Entity
from .utils import distance


def is_targetable(entity: Entity) -> bool:
    """Only active enemy or unknown contacts are effect candidates."""

    return entity.active and entity.allegiance in {"enemy", "unknown"} and entity.domain != "non_threat"


def payload_match(payload: str, target: Entity) -> float:
    if not is_targetable(target):
        return 0.0
    if payload == "cuas":
        return 1.0 if target.entity_type == "enemy_drone" else 0.1
    if payload == "ew":
        return 0.95 if target.entity_type in {"enemy_drone", "enemy_ew", "enemy_unknown", "unknown_contact"} else 0.35
    if payload == "isr":
        return 0.95 if target.entity_type in {"enemy_unknown", "unknown_contact", "enemy_ew"} or target.confidence < 0.75 else 0.55
    if payload == "effect":
        return 0.9 if target.domain in {"ground", "fixed"} and target.entity_type != "enemy_drone" else 0.15
    if payload == "comms":
        return 0.0
    return 0.0


def proximity_norm(point_a: list[float], point_b: list[float], max_distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - distance(point_a, point_b) / max_distance))


def compute_network_support(friendlies: list[Entity], enemies: list[Entity]) -> dict[str, bool]:
    """Compute simple COMMS relay support with abstract enemy EW degradation."""

    comms_nodes = [f for f in friendlies if f.active and f.payload_type == "comms"]
    support: dict[str, bool] = {}
    for friendly in friendlies:
        supported = friendly.payload_type == "comms"
        for comms in comms_nodes:
            radius = comms.network_radius
            for enemy in enemies:
                if enemy.active and enemy.entity_type == "enemy_ew" and distance(enemy.position, comms.position) < enemy.effect_range * 1.5:
                    radius *= 0.65
            if distance(friendly.position, comms.position) <= radius:
                supported = True
        friendly.network_supported = supported
        support[friendly.id] = supported
    return support


def global_priority_score(target: Entity, friendlies: list[Entity], objective: list[float], map_diag: float) -> float:
    if not is_targetable(target):
        return 0.0
    objective_score = proximity_norm(target.position, objective, map_diag)
    friendly_score = max((proximity_norm(target.position, f.position, map_diag) for f in friendlies if f.active), default=0.0)
    speed_score = min(1.0, target.speed / 45.0)
    payload_score = max((payload_match(f.payload_type, target) for f in friendlies if f.active), default=0.0)
    confidence_score = target.confidence
    network_threat = 1.0 if target.entity_type == "enemy_ew" else 0.6 if target.entity_type == "enemy_drone" else 0.2
    score = (
        4.0 * target.threat_level
        + 20.0 * objective_score
        + 10.0 * friendly_score
        + 10.0 * speed_score
        + 10.0 * payload_score
        + 5.0 * confidence_score
        + 5.0 * network_threat
    )
    return round(score, 2)


def local_priority_score(
    friendly: Entity,
    target: Entity,
    central_target_id: str | None,
    map_diag: float,
    path_accessibility: float = 1.0,
) -> float:
    if friendly.payload_type == "comms" or not is_targetable(target):
        return 0.0
    proximity = proximity_norm(friendly.position, target.position, map_diag)
    central_bonus = 1.0 if central_target_id == target.id else 0.0
    risk = proximity * (target.threat_level / 10.0) if target.threat_level >= 7 else 0.0
    cooldown = 1.0 if friendly.effect_cooldown_remaining > 0 or friendly.magazine == 0 else 0.0
    score = (
        3.0 * target.threat_level
        + 25.0 * proximity
        + 20.0 * payload_match(friendly.payload_type, target)
        + 10.0 * path_accessibility
        + 10.0 * central_bonus
        - 15.0 * risk
        - 10.0 * cooldown
    )
    return round(max(0.0, score), 2)
