from aries.config_loader import load_config, load_scenario
from aries.local_agent import terrain_accessibility
from aries.models import Entity
from aries.simulation import Simulation
from aries.terrain import Terrain


def test_assignment_events_are_logged_only_on_change():
    config = load_config()
    scenario = load_scenario("scenarios/demo_scenario.json", config)
    sim = Simulation(scenario, config)

    for _ in range(5):
        sim.step()

    assignment_events = [event for event in sim.state.events if event.event_type == "assign"]
    assert len(assignment_events) <= 2


def test_path_refresh_is_not_per_entity_per_step():
    config = load_config()
    scenario = load_scenario("scenarios/demo_scenario.json", config)
    sim = Simulation(scenario, config)
    calls = 0
    original = sim.local_agent.update_path

    def counted_update_path(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    sim.local_agent.update_path = counted_update_path
    for _ in range(5):
        sim.step()

    assert calls < len(sim.friendlies) * 5


def test_terrain_accessibility_is_bounded():
    terrain = Terrain.generate(100, 100, seed=1)
    friendly = Entity.from_dict({
        "id": "F",
        "name": "Friendly",
        "allegiance": "friendly",
        "domain": "ground",
        "entity_type": "friendly_effect",
        "payload_type": "effect",
        "position": [10, 10],
    })
    target = Entity.from_dict({
        "id": "E",
        "name": "Enemy",
        "allegiance": "enemy",
        "domain": "ground",
        "entity_type": "enemy_ground_vehicle",
        "position": [90, 90],
    })

    accessibility = terrain_accessibility(friendly, target, terrain)

    assert 0.15 <= accessibility <= 1.0


def test_demo_scenario_has_readable_duration():
    config = load_config()
    scenario = load_scenario("scenarios/demo_scenario.json", config)
    sim = Simulation(scenario, config)

    for _ in range(30):
        sim.step()
        assert not sim.state.mission_done

    for _ in range(170):
        sim.step()
        if sim.state.mission_done:
            break

    assert sim.state.mission_done
    assert sim.state.outcome == "ALL_THREATS_DISABLED"
    assert len(sim.state.events) < 80


def test_replay_recording_can_be_disabled():
    config = load_config()
    config["simulation"]["record_replay"] = False
    scenario = load_scenario("scenarios/simple_test_scenario.json", config)
    sim = Simulation(scenario, config)

    for _ in range(3):
        sim.step()

    assert sim.state.replay_frames == []
