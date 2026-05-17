from __future__ import annotations

import subprocess
import sys

from aries.config_loader import load_config, load_scenario
from aries.replay import load_replay, save_replay
from aries.simulation import Simulation


def test_replay_save_load_and_cli(tmp_path):
    config = load_config()
    config["paths"]["replay_folder"] = str(tmp_path)
    scenario = load_scenario("scenarios/simple_test_scenario.json", config)
    sim = Simulation(scenario, config)
    for _ in range(3):
        sim.step()

    replay_path = save_replay(sim, config)
    payload = load_replay(replay_path)

    assert payload["scenario_name"] == "Simple Test Scenario"
    assert len(payload["frames"]) == len(sim.state.replay_frames)
    assert payload["frames"][-1]["outcome"] == sim.state.outcome

    result = subprocess.run(
        [sys.executable, "run_replay.py", str(replay_path)],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0
    assert "Replay: Simple Test Scenario" in result.stdout
    assert "Frames:" in result.stdout
