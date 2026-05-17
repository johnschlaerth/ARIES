import math

from aries.models import Entity
from aries.scoring import global_priority_score, is_targetable, local_priority_score, payload_match


def enemy(**overrides):
    data = {
        "id": "E",
        "name": "Enemy",
        "allegiance": "enemy",
        "domain": "ground",
        "entity_type": "enemy_ground_vehicle",
        "position": [50, 50],
        "speed": 5,
        "threat_level": 5,
        "confidence": 0.8,
    }
    data.update(overrides)
    return Entity.from_dict(data)


def friendly(payload="effect"):
    return Entity.from_dict({
        "id": "F",
        "name": "Friendly",
        "allegiance": "friendly",
        "domain": "ground",
        "entity_type": f"friendly_{payload}" if payload != "effect" else "friendly_effect",
        "payload_type": payload,
        "position": [0, 0],
        "speed": 10,
    })


def test_higher_threat_increases_global_score():
    f = [friendly()]
    low = global_priority_score(enemy(threat_level=3), f, [100, 100], 200)
    high = global_priority_score(enemy(threat_level=9), f, [100, 100], 200)
    assert high > low


def test_closer_to_objective_scores_higher():
    f = [friendly()]
    far = global_priority_score(enemy(position=[0, 0]), f, [100, 100], 200)
    near = global_priority_score(enemy(position=[95, 95]), f, [100, 100], 200)
    assert near > far


def test_drone_speed_increases_score():
    f = [friendly("cuas")]
    slow = global_priority_score(enemy(entity_type="enemy_drone", domain="air", speed=5), f, [100, 100], 200)
    fast = global_priority_score(enemy(entity_type="enemy_drone", domain="air", speed=40), f, [100, 100], 200)
    assert fast > slow


def test_payload_matching_increases_local_score():
    cuas = friendly("cuas")
    drone = enemy(entity_type="enemy_drone", domain="air")
    ground = enemy(entity_type="enemy_ground_vehicle", domain="ground")
    assert payload_match("cuas", drone) > payload_match("cuas", ground)
    assert local_priority_score(cuas, drone, drone.id, math.hypot(100, 100)) > local_priority_score(cuas, ground, ground.id, math.hypot(100, 100))


def test_neutral_non_threat_is_not_targeted():
    neutral = Entity.from_dict({
        "id": "N",
        "name": "Puppy",
        "allegiance": "neutral",
        "domain": "non_threat",
        "entity_type": "non_threat_animal",
    })
    assert not is_targetable(neutral)

