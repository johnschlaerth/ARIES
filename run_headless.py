"""Run a complete ARIES mission without Pygame."""

from __future__ import annotations

import argparse

from aries.config_loader import load_config, load_scenario, resolve_project_path
from aries.replay import save_replay
from aries.report_writer import write_reports
from aries.simulation import Simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ARIES simulation headlessly and write reports.")
    parser.add_argument("--scenario", default=None, help="Scenario JSON path relative to project root or absolute path.")
    parser.add_argument("--max-steps", type=int, default=None, help="Override maximum simulation steps for this run.")
    parser.add_argument("--no-replay", action="store_true", help="Skip replay JSON export.")
    args = parser.parse_args()

    config = load_config()
    if args.max_steps is not None:
        config["simulation"]["max_steps"] = args.max_steps
    if args.no_replay:
        config["simulation"]["record_replay"] = False
    scenario_path = args.scenario or config["paths"]["scenario_file"]
    scenario = load_scenario(scenario_path, config)
    sim = Simulation(scenario, config)
    while not sim.state.mission_done:
        sim.step()

    report_paths = write_reports(sim, config)
    replay_path = None if args.no_replay else save_replay(sim, config)
    print(f"ARIES headless run complete: outcome={sim.state.outcome} steps={sim.state.step}")
    print(f"Mission report: {report_paths['txt']}")
    print(f"Summary JSON: {report_paths['summary']}")
    if replay_path:
        print(f"Replay JSON: {resolve_project_path(config, replay_path)}")


if __name__ == "__main__":
    main()
