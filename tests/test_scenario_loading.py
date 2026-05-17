import json

import pytest

from aries.config_loader import load_config, load_scenario


def test_scenario_json_loads():
    scenario = load_scenario("scenarios/demo_scenario.json", load_config())
    assert scenario.scenario_name == "ARIES Demo Scenario"
    assert len(scenario.friendly_entities) == 5


def test_defaults_are_applied():
    scenario = load_scenario("scenarios/simple_test_scenario.json", load_config())
    entity = scenario.friendly_entities[0]
    assert entity.health == 100.0
    assert entity.alive is True


def test_invalid_scenario_raises_useful_error(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"scenario_name": "Bad"}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing required field"):
        load_scenario(path, load_config())

