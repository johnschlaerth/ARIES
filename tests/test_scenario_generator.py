from aries.config_loader import load_config, load_or_generate_scenario, load_scenario
from aries.scenario_builder import build_scenario_payload, make_entity
from aries.scenario_generator import generate_scenario_payload, write_generated_scenario
from aries.simulation import Simulation


def test_generated_scenario_respects_sides_and_caps():
    config = load_config()
    payload = generate_scenario_payload(config, seed=123)
    width = payload["map"]["width"]

    assert len(payload["friendly_entities"]) == 5
    assert config["scenario_generation"]["min_enemies"] <= len(payload["enemy_entities"]) <= config["scenario_generation"]["max_enemies"]
    assert len(payload["neutral_entities"]) <= config["scenario_generation"]["max_neutrals"]
    assert all(entity["position"][0] <= width * 0.32 for entity in payload["friendly_entities"])
    assert all(entity["position"][0] >= width * 0.70 for entity in payload["enemy_entities"])


def test_generated_scenario_seed_is_repeatable():
    config = load_config()
    first = generate_scenario_payload(config, seed=456)
    second = generate_scenario_payload(config, seed=456)
    third = generate_scenario_payload(config, seed=789)

    assert first == second
    assert first != third


def test_generated_scenario_can_be_written_and_loaded(tmp_path):
    config = load_config()
    config["scenario_generation"]["generated_scenario_file"] = str(tmp_path / "generated.json")
    payload = generate_scenario_payload(config, seed=321)
    path = write_generated_scenario(payload, config)
    scenario = load_scenario(path, config)

    assert scenario.scenario_name.startswith("Generated ARIES Scenario")
    assert len(scenario.friendly_entities) == 5


def test_load_or_generate_forces_random_seed():
    config = load_config()
    first = load_or_generate_scenario(config, force_random=True, seed=111)
    second = load_or_generate_scenario(config, force_random=True, seed=111)

    assert [e.position for e in first.enemy_entities] == [e.position for e in second.enemy_entities]


def test_random_headless_run_completes_with_capped_entities():
    config = load_config()
    scenario = load_or_generate_scenario(config, force_random=True, seed=222)
    sim = Simulation(scenario, config)
    while not sim.state.mission_done:
        sim.step()

    assert sim.state.outcome in {"ALL_THREATS_DISABLED", "MAX_STEPS_REACHED", "OBJECTIVE_REACHED_BY_ENEMY"}
    assert len(sim.enemies) <= config["scenario_generation"]["max_enemies"]


def test_builder_payload_schema_from_placed_entities():
    config = load_config()
    entities = [
        make_entity("1", (100, 300), []),
        make_entity("6", (850, 120), []),
        make_entity("0", (500, 300), []),
    ]
    payload = build_scenario_payload(entities, config)

    assert payload["friendly_entities"]
    assert payload["enemy_entities"]
    assert payload["neutral_entities"]
    assert payload["map"]["objective_position"][0] > payload["map"]["friendly_base_position"][0]
