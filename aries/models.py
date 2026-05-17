"""Dataclasses used by the simulator.

The models are intentionally plain dataclasses instead of ORM or framework
objects. That keeps the demo easy to inspect, serialize, and test.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .constants import DOMAINS, ENTITY_TYPES, PAYLOAD_TYPES


def clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value into an inclusive range."""

    return max(low, min(high, value))


@dataclass
class Entity:
    """One object in the synthetic battlespace."""

    id: str
    name: str
    allegiance: str
    domain: str
    entity_type: str
    payload_type: str = "none"
    position: list[float] = field(default_factory=lambda: [0.0, 0.0])
    velocity: list[float] = field(default_factory=lambda: [0.0, 0.0])
    speed: float = 0.0
    health: float = 100.0
    alive: bool = True
    disabled: bool = False
    threat_level: int = 1
    confidence: float = 1.0
    classification_source: str = "scenario"
    description: str = ""
    priority_score_global: float = 0.0
    priority_score_local: float = 0.0
    target_id: str | None = None
    path: list[list[float]] = field(default_factory=list)
    effect_range: float = 80.0
    effect_cooldown_steps: int = 4
    effect_cooldown_remaining: int = 0
    effect_probability: float = 0.8
    magazine: int | None = None
    network_radius: float = 180.0
    sensor_radius: float = 160.0
    status_text: str = "OK"
    network_supported: bool = False
    suppressed_steps: int = 0
    revealed: bool = True
    first_seen_step: int | None = None
    neutralized_step: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """Create an entity while applying safe defaults and validation."""

        merged = {
            "payload_type": "none",
            "position": [0.0, 0.0],
            "velocity": [0.0, 0.0],
            "speed": 0.0,
            "health": 100.0,
            "alive": True,
            "disabled": False,
            "threat_level": 1,
            "confidence": 1.0,
            "classification_source": "scenario",
            "description": "",
            "effect_range": 80.0,
            "effect_cooldown_steps": 4,
            "effect_cooldown_remaining": 0,
            "effect_probability": 0.8,
            "magazine": None,
            "network_radius": 180.0,
            "sensor_radius": 160.0,
            "status_text": "OK",
        }
        merged.update(data)
        required = ["id", "name", "allegiance", "domain", "entity_type"]
        missing = [key for key in required if key not in merged]
        if missing:
            raise ValueError(f"Entity missing required fields: {missing}")
        if merged["domain"] not in DOMAINS:
            raise ValueError(f"Invalid domain for {merged['id']}: {merged['domain']}")
        if merged["entity_type"] not in ENTITY_TYPES:
            raise ValueError(f"Invalid entity_type for {merged['id']}: {merged['entity_type']}")
        if merged["payload_type"] not in PAYLOAD_TYPES:
            raise ValueError(f"Invalid payload_type for {merged['id']}: {merged['payload_type']}")
        merged["threat_level"] = int(clamp(int(merged["threat_level"]), 1, 10))
        merged["confidence"] = clamp(float(merged["confidence"]), 0.0, 1.0)
        return cls(**{k: v for k, v in merged.items() if k in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/CSV friendly representation."""

        return asdict(self)

    @property
    def active(self) -> bool:
        """True when an entity should move and participate in effects."""

        return self.alive and not self.disabled and self.health > 0


@dataclass
class ClassificationResult:
    """Validated image classification payload."""

    image_path: str
    name: str
    allegiance: str
    domain: str
    entity_type: str
    threat_level: int
    confidence: float
    description: str
    rationale: str
    should_spawn_in_simulation: bool
    recommended_symbol: str = "?"
    safety_notes: str = ""
    source: str = "mock"

    @classmethod
    def safe_unknown(cls, image_path: str, source: str = "fallback") -> "ClassificationResult":
        return cls(
            image_path=image_path,
            name="unknown contact",
            allegiance="unknown",
            domain="ground",
            entity_type="unknown_contact",
            threat_level=3,
            confidence=0.2,
            description="Unable to classify image with high confidence.",
            rationale="Fallback classification used after invalid or unavailable result.",
            should_spawn_in_simulation=True,
            recommended_symbol="?",
            safety_notes="Conservative unknown; not automatically treated as enemy.",
            source=source,
        )

    @classmethod
    def from_payload(cls, image_path: str, payload: dict[str, Any], source: str) -> "ClassificationResult":
        required = [
            "name",
            "allegiance",
            "domain",
            "entity_type",
            "threat_level",
            "confidence",
            "description",
            "rationale",
            "should_spawn_in_simulation",
        ]
        if any(key not in payload for key in required):
            return cls.safe_unknown(image_path, source="invalid")
        if payload["domain"] not in DOMAINS or payload["entity_type"] not in ENTITY_TYPES:
            return cls.safe_unknown(image_path, source="invalid")
        return cls(
            image_path=image_path,
            name=str(payload["name"]),
            allegiance=str(payload["allegiance"]),
            domain=str(payload["domain"]),
            entity_type=str(payload["entity_type"]),
            threat_level=int(clamp(int(payload["threat_level"]), 1, 10)),
            confidence=clamp(float(payload["confidence"]), 0.0, 1.0),
            description=str(payload["description"]),
            rationale=str(payload["rationale"]),
            should_spawn_in_simulation=bool(payload["should_spawn_in_simulation"]),
            recommended_symbol=str(payload.get("recommended_symbol", "?")),
            safety_notes=str(payload.get("safety_notes", "")),
            source=source,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    """One timestamped simulation event."""

    step: int
    event_type: str
    message: str
    actor_id: str | None = None
    target_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Scenario:
    """Loaded scenario and map metadata."""

    scenario_name: str
    description: str
    map: dict[str, Any]
    friendly_entities: list[Entity]
    enemy_entities: list[Entity]
    neutral_entities: list[Entity]
    image_assignments: list[dict[str, Any]] = field(default_factory=list)

    @property
    def all_entities(self) -> list[Entity]:
        return self.friendly_entities + self.enemy_entities + self.neutral_entities
