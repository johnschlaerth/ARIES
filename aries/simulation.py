"""Deterministic ARIES simulation loop."""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field

from .battle_manager import BattleManager
from .effects import apply_effects, apply_enemy_counterfire, update_cooldowns
from .local_agent import LocalAgent
from .models import Entity, Event, Scenario
from .pathfinding import astar_path, direct_path
from .scoring import compute_network_support, is_targetable
from .terrain import Terrain
from .utils import distance, move_toward


@dataclass
class SimulationState:
    step: int = 0
    paused: bool = True
    mission_done: bool = False
    outcome: str = "RUNNING"
    events: list[Event] = field(default_factory=list)
    replay_frames: list[dict] = field(default_factory=list)
    network_uptime_samples: list[float] = field(default_factory=list)


class Simulation:
    """Owns all mutable mission state and advances it one timestep at a time."""

    def __init__(self, scenario: Scenario, config: dict):
        self.original_scenario = copy.deepcopy(scenario)
        self.config = config
        self.scenario = copy.deepcopy(scenario)
        sim_cfg = config.get("simulation", {})
        self.max_steps = int(sim_cfg.get("max_steps", 600))
        self.time_step_seconds = float(sim_cfg.get("time_step_seconds", 1.0))
        self.record_replay = bool(sim_cfg.get("record_replay", True))
        self.rng = random.Random(int(sim_cfg.get("seed", self.scenario.map.get("terrain_seed", 42))))
        self.terrain = Terrain.generate(
            int(self.scenario.map["width"]),
            int(self.scenario.map["height"]),
            int(self.scenario.map.get("terrain_seed", sim_cfg.get("seed", 42))),
            grid_size=int(config.get("scenario_generation", {}).get("terrain_grid_size", 120)),
        )
        self.state = SimulationState(paused=bool(sim_cfg.get("start_paused", True)))
        self.manager = BattleManager(
            self.scenario.map["objective_position"],
            int(self.scenario.map["width"]),
            int(self.scenario.map["height"]),
        )
        self.local_agent = LocalAgent(int(self.scenario.map["width"]), int(self.scenario.map["height"]))
        self._path_goals: dict[str, tuple[str | None, list[float]]] = {}
        self._last_assignment_snapshot: dict[str, str] = {}
        self._initialize_enemy_paths()

    @property
    def friendlies(self) -> list[Entity]:
        return self.scenario.friendly_entities

    @property
    def enemies(self) -> list[Entity]:
        return self.scenario.enemy_entities

    @property
    def neutrals(self) -> list[Entity]:
        return self.scenario.neutral_entities

    @property
    def all_entities(self) -> list[Entity]:
        return self.scenario.all_entities

    def reset(self) -> None:
        self.__init__(copy.deepcopy(self.original_scenario), self.config)

    def log(self, event_type: str, message: str, actor_id: str | None = None, target_id: str | None = None) -> None:
        self.state.events.append(Event(self.state.step, event_type, message, actor_id, target_id))

    def _initialize_enemy_paths(self) -> None:
        objective = self.scenario.map["objective_position"]
        for enemy in self.enemies:
            if enemy.domain == "air":
                enemy.path = direct_path(enemy.position, objective)
            elif enemy.domain == "ground":
                enemy.path = astar_path(enemy.position, objective, self.terrain)

    def _network_sample(self) -> None:
        supported = compute_network_support(self.friendlies, self.enemies)
        if supported:
            self.state.network_uptime_samples.append(sum(1 for v in supported.values() if v) / len(supported))

    def _support_point(self) -> list[float]:
        base = self.scenario.map["friendly_base_position"]
        objective = self.scenario.map["objective_position"]
        return [(base[0] + objective[0]) / 2.0, (base[1] + objective[1]) / 2.0]

    def _move_entity_along_path(self, entity: Entity, speed_scale: float = 1.0) -> None:
        if not entity.active:
            entity.velocity = [0.0, 0.0]
            return
        if not entity.path:
            entity.velocity = [0.0, 0.0]
            return
        goal = entity.path[1] if len(entity.path) > 1 else entity.path[0]
        terrain_penalty = self.terrain.cost_at(entity.position) if entity.domain == "ground" else 1.0
        suppressed_penalty = 0.45 if entity.suppressed_steps > 0 else 1.0
        max_distance = entity.speed * self.time_step_seconds * speed_scale * suppressed_penalty / max(1.0, terrain_penalty * 0.45)
        new_pos, velocity = move_toward(entity.position, goal, max_distance)
        entity.position = new_pos
        entity.velocity = velocity
        if distance(entity.position, goal) < 3.0 and len(entity.path) > 1:
            entity.path.pop(0)

    def _move_friendlies(self) -> None:
        central = self.manager.assignments
        targets_by_id = {enemy.id: enemy for enemy in self.enemies}
        support_point = self._support_point()
        for friendly in self.friendlies:
            target = self.local_agent.choose_target(friendly, self.enemies, self.terrain, central.get(friendly.id))
            goal = support_point if friendly.payload_type == "comms" else target.position if target else friendly.position
            target_id = target.id if target else None
            if self._should_refresh_path(friendly, goal, target_id):
                self.local_agent.update_path(friendly, target, self.terrain, support_point)
                self._path_goals[friendly.id] = (target_id, list(goal))
            if friendly.payload_type == "comms" or (target and distance(friendly.position, target.position) > friendly.effect_range * 0.75):
                self._move_entity_along_path(friendly, speed_scale=1.0)
            elif target:
                friendly.velocity = [0.0, 0.0]
                friendly.status_text = f"IN RANGE {targets_by_id[target.id].id}"

    def _should_refresh_path(self, friendly: Entity, goal: list[float], target_id: str | None) -> bool:
        """Refresh A* paths only when the old path is stale.

        Ground paths are relatively expensive compared with all other MVP logic.
        This keeps routing responsive while avoiding repeated identical searches.
        """

        if not friendly.active:
            return False
        if not friendly.path:
            return True
        previous = self._path_goals.get(friendly.id)
        if previous is None:
            return True
        previous_target_id, previous_goal = previous
        if previous_target_id != target_id:
            return True
        if distance(previous_goal, goal) > 35.0:
            return True
        return self.state.step % 12 == 1

    def _move_enemies(self) -> None:
        objective = self.scenario.map["objective_position"]
        for enemy in self.enemies:
            if not enemy.active:
                enemy.velocity = [0.0, 0.0]
                continue
            if not enemy.path:
                enemy.path = direct_path(enemy.position, objective) if enemy.domain == "air" else astar_path(enemy.position, objective, self.terrain)
            self._move_entity_along_path(enemy, speed_scale=1.0)
            if distance(enemy.position, objective) < 16.0:
                self.state.mission_done = True
                self.state.outcome = "OBJECTIVE_REACHED_BY_ENEMY"
                self.log("mission", "Enemy reached the objective", enemy.id)

    def _check_end_conditions(self) -> None:
        if self.state.mission_done:
            return
        if not any(is_targetable(enemy) for enemy in self.enemies):
            self.state.mission_done = True
            self.state.outcome = "ALL_THREATS_DISABLED"
            self.log("mission", "All targetable threats disabled")
        elif not any(f.active for f in self.friendlies):
            self.state.mission_done = True
            self.state.outcome = "ALL_FRIENDLIES_DISABLED"
            self.log("mission", "All friendly ARIES units disabled")
        elif self.state.step >= self.max_steps:
            self.state.mission_done = True
            self.state.outcome = "MAX_STEPS_REACHED"
            self.log("mission", "Maximum timestep reached")

    def step(self) -> None:
        if self.state.mission_done:
            return
        self.state.step += 1
        self._network_sample()
        assignments = self.manager.update(self.friendlies, self.enemies)
        if self.state.step == 1:
            self.log("start", f"Scenario started: {self.scenario.scenario_name}")
        if assignments and assignments != self._last_assignment_snapshot:
            self.log("assign", f"Central assignments updated: {assignments}")
            self._last_assignment_snapshot = dict(assignments)
        self._move_friendlies()
        self._move_enemies()
        self.state.events.extend(apply_effects(self.friendlies, self.enemies, self.rng, self.state.step))
        self.state.events.extend(apply_enemy_counterfire(self.friendlies, self.enemies, self.rng, self.state.step))
        update_cooldowns(self.all_entities)
        self._check_end_conditions()
        if self.record_replay:
            self._record_replay_frame()

    def _record_replay_frame(self) -> None:
        self.state.replay_frames.append(
            {
                "step": self.state.step,
                "outcome": self.state.outcome,
                "entities": [entity.to_dict() for entity in self.all_entities],
                "events": [event.to_dict() for event in self.state.events[-5:]],
            }
        )
