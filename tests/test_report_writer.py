import json
import csv

from aries.config_loader import load_config, load_scenario
from aries.report_writer import write_reports
from aries.simulation import Simulation


def test_report_files_created(tmp_path):
    config = load_config()
    config["paths"]["report_folder"] = str(tmp_path)
    scenario = load_scenario("scenarios/simple_test_scenario.json", config)
    sim = Simulation(scenario, config)
    sim.step()
    paths = write_reports(sim, config)
    assert paths["txt"].exists()
    assert paths["entities"].exists()
    assert paths["events"].exists()
    assert paths["summary"].exists()


def test_entity_csv_has_required_columns(tmp_path):
    config = load_config()
    config["paths"]["report_folder"] = str(tmp_path)
    sim = Simulation(load_scenario("scenarios/simple_test_scenario.json", config), config)
    sim.step()
    paths = write_reports(sim, config)
    header = paths["entities"].read_text(encoding="utf-8").splitlines()[0]
    assert "id" in header
    assert "entity_type" in header
    assert "position" in header


def test_entity_csv_preserves_structured_fields_as_json(tmp_path):
    config = load_config()
    config["paths"]["report_folder"] = str(tmp_path)
    sim = Simulation(load_scenario("scenarios/simple_test_scenario.json", config), config)
    sim.step()
    paths = write_reports(sim, config)
    with paths["entities"].open("r", encoding="utf-8", newline="") as handle:
        first = next(csv.DictReader(handle))
    position = json.loads(first["position"])
    assert isinstance(position, list)
    assert len(position) == 2


def test_summary_json_valid(tmp_path):
    config = load_config()
    config["paths"]["report_folder"] = str(tmp_path)
    sim = Simulation(load_scenario("scenarios/simple_test_scenario.json", config), config)
    sim.step()
    paths = write_reports(sim, config)
    payload = json.loads(paths["summary"].read_text(encoding="utf-8"))
    assert payload["scenario_name"] == "Simple Test Scenario"
