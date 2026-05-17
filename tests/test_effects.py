import random

from aries.effects import apply_effects, update_cooldowns
from aries.models import Entity


def make(entity_type, payload="none", allegiance="enemy", domain="ground", position=None):
    return Entity.from_dict({
        "id": entity_type,
        "name": entity_type,
        "allegiance": allegiance,
        "domain": domain,
        "entity_type": entity_type,
        "payload_type": payload,
        "position": position or [0, 0],
        "speed": 0,
        "threat_level": 8 if allegiance == "enemy" else 1,
        "effect_range": 100,
        "effect_probability": 1.0,
        "effect_cooldown_steps": 2,
        "magazine": 2 if payload in {"cuas", "effect"} else None,
    })


def test_cuas_neutralizes_drone_in_range():
    cuas = make("friendly_cuas", "cuas", "friendly", position=[0, 0])
    drone = make("enemy_drone", domain="air", position=[20, 0])
    cuas.target_id = drone.id
    events = apply_effects([cuas], [drone], random.Random(1), 1)
    assert drone.disabled
    assert any(e.event_type == "neutralize" for e in events)


def test_cuas_does_not_target_neutral():
    cuas = make("friendly_cuas", "cuas", "friendly", position=[0, 0])
    neutral = make("non_threat_object", allegiance="neutral", domain="non_threat", position=[20, 0])
    cuas.target_id = neutral.id
    apply_effects([cuas], [neutral], random.Random(1), 1)
    assert neutral.active


def test_ew_suppresses_without_kill():
    ew = make("friendly_ew", "ew", "friendly", position=[0, 0])
    target = make("enemy_drone", domain="air", position=[20, 0])
    ew.target_id = target.id
    apply_effects([ew], [target], random.Random(1), 1)
    assert target.active
    assert target.suppressed_steps > 0


def test_disabled_entity_remains_inactive():
    target = make("enemy_drone", domain="air")
    target.disabled = True
    target.alive = False
    assert not target.active
    assert target.status_text != "REMOVED"


def test_cooldown_prevents_repeated_effect():
    cuas = make("friendly_cuas", "cuas", "friendly", position=[0, 0])
    d1 = make("enemy_drone", domain="air", position=[20, 0])
    d2 = make("enemy_drone", domain="air", position=[25, 0])
    cuas.target_id = d1.id
    apply_effects([cuas], [d1], random.Random(1), 1)
    cuas.target_id = d2.id
    events = apply_effects([cuas], [d2], random.Random(1), 2)
    assert d2.active
    assert any(e.event_type == "cooldown" for e in events)
    update_cooldowns([cuas])
    update_cooldowns([cuas])
    assert cuas.effect_cooldown_remaining == 0

