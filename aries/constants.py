"""Shared constants for the ARIES MVP."""

ALLEGIANCES = {"friendly", "enemy", "neutral", "unknown"}
DOMAINS = {"ground", "air", "fixed", "non_threat"}
PAYLOAD_TYPES = {"comms", "ew", "isr", "cuas", "effect", "none"}

FRIENDLY_TYPES = {
    "friendly_comms",
    "friendly_ew",
    "friendly_isr",
    "friendly_cuas",
    "friendly_effect",
    "friendly_human",
    "friendly_vehicle",
}

ENEMY_TYPES = {
    "enemy_drone",
    "enemy_ground_vehicle",
    "enemy_ew",
    "enemy_infantry",
    "enemy_unknown",
}

NON_TARGET_TYPES = {
    "neutral_civilian",
    "friendly_human",
    "friendly_vehicle",
    "non_threat_animal",
    "non_threat_object",
}

ENTITY_TYPES = FRIENDLY_TYPES | ENEMY_TYPES | NON_TARGET_TYPES | {"unknown_contact"}

DEFAULT_MAP_WIDTH = 1000
DEFAULT_MAP_HEIGHT = 700

