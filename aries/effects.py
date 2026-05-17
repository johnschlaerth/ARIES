"""Abstract effect resolution.

This module deliberately models effects as local simulation state changes only.
It does not contain real jamming, weapons, fire-control, or hardware behavior.
"""

from __future__ import annotations

import random

from .models import Entity, Event
from .scoring import is_targetable, payload_match
from .utils import distance


def _cooldown_ready(actor: Entity) -> bool:
    return actor.effect_cooldown_remaining <= 0 and actor.magazine != 0


def _start_cooldown(actor: Entity) -> None:
    actor.effect_cooldown_remaining = actor.effect_cooldown_steps
    if actor.magazine is not None and actor.magazine > 0:
        actor.magazine -= 1


def apply_effects(friendlies: list[Entity], enemies: list[Entity], rng: random.Random, step: int) -> list[Event]:
    events: list[Event] = []
    for actor in friendlies:
        if not actor.active:
            continue
        if actor.payload_type == "comms":
            for friendly in friendlies:
                if friendly.id != actor.id and distance(actor.position, friendly.position) <= actor.network_radius:
                    friendly.network_supported = True
            actor.status_text = "RELAY"
            continue

        target = next((enemy for enemy in enemies if enemy.id == actor.target_id), None)
        if not target or not is_targetable(target):
            continue
        if distance(actor.position, target.position) > actor.effect_range:
            continue

        if actor.payload_type == "isr":
            if target.confidence < 0.95 or target.entity_type in {"enemy_unknown", "unknown_contact"}:
                target.confidence = min(0.95, target.confidence + 0.25)
                target.revealed = True
                if target.entity_type == "unknown_contact":
                    target.entity_type = "enemy_unknown"
                    target.allegiance = "enemy"
                events.append(Event(step, "classify", f"{actor.name} improved classification on {target.name}", actor.id, target.id))
            continue

        if actor.payload_type == "ew":
            was_suppressed = target.suppressed_steps > 0
            target.suppressed_steps = max(target.suppressed_steps, 4)
            target.status_text = "SUPPRESSED"
            target.velocity = [target.velocity[0] * 0.6, target.velocity[1] * 0.6]
            if not was_suppressed:
                events.append(Event(step, "suppress", f"{actor.name} suppressed {target.name}", actor.id, target.id))
            continue

        if actor.payload_type in {"cuas", "effect"}:
            if not _cooldown_ready(actor):
                events.append(Event(step, "cooldown", f"{actor.name} effect unavailable", actor.id, target.id))
                continue
            if payload_match(actor.payload_type, target) < 0.5:
                continue
            success = rng.random() <= actor.effect_probability
            _start_cooldown(actor)
            if success:
                target.alive = False
                target.disabled = True
                target.health = 0
                target.status_text = "X"
                target.neutralized_step = step
                events.append(Event(step, "neutralize", f"{actor.name} neutralized {target.name} (abstract)", actor.id, target.id))
            else:
                events.append(Event(step, "effect_failed", f"{actor.name} failed to neutralize {target.name}", actor.id, target.id))
    return events


def apply_enemy_counterfire(friendlies: list[Entity], enemies: list[Entity], rng: random.Random, step: int) -> list[Event]:
    """Enemies engage friendly units that come within their attack range."""
    events: list[Event] = []
    for attacker in enemies:
        if not attacker.active or attacker.effect_range <= 0:
            continue
        if attacker.effect_cooldown_remaining > 0:
            continue

        in_range = [f for f in friendlies if f.active and distance(attacker.position, f.position) <= attacker.effect_range]
        if not in_range:
            continue

        if attacker.entity_type == "enemy_ew":
            # EW enemies jam/suppress all friendlies in range rather than killing them
            for target in in_range:
                if target.suppressed_steps < 6:
                    target.suppressed_steps = 6
                    target.status_text = "JAMMED"
                    events.append(Event(step, "friendly_jammed", f"{attacker.name} jammed {target.name}", attacker.id, target.id))
            attacker.effect_cooldown_remaining = attacker.effect_cooldown_steps
            continue

        # All other enemies attempt to hit one random friendly in range
        target = rng.choice(in_range)
        attacker.effect_cooldown_remaining = attacker.effect_cooldown_steps
        if rng.random() <= attacker.effect_probability:
            damage = float(attacker.threat_level * 3)
            target.health = max(0.0, target.health - damage)
            if target.health <= 0.0:
                target.alive = False
                target.disabled = True
                target.status_text = "X"
                events.append(Event(step, "friendly_lost", f"{attacker.name} eliminated {target.name}", attacker.id, target.id))
            else:
                target.status_text = f"DMG {int(target.health)}%"
                events.append(Event(step, "friendly_hit", f"{attacker.name} hit {target.name} ({int(target.health)}% HP)", attacker.id, target.id))
    return events


def update_cooldowns(entities: list[Entity]) -> None:
    for entity in entities:
        if entity.effect_cooldown_remaining > 0:
            entity.effect_cooldown_remaining -= 1
        if entity.suppressed_steps > 0:
            entity.suppressed_steps -= 1
            if entity.suppressed_steps == 0 and entity.active:
                entity.status_text = "OK"
