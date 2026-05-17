"""End-to-end non-GUI readiness checks for ARIES."""

from __future__ import annotations

from .classifier import ImageClassifier
from .config_loader import load_config, load_or_generate_scenario, resolve_project_path
from .report_writer import write_reports
from .simulation import Simulation


def run_self_check(write_outputs: bool = False) -> tuple[bool, list[str]]:
    """Run a compact readiness check that does not require Pygame."""

    messages: list[str] = []
    config = load_config()
    config["simulation"]["record_replay"] = False
    scenario = load_or_generate_scenario(config, force_random=True, seed=42)
    sim = Simulation(scenario, config)
    while not sim.state.mission_done:
        sim.step()
    messages.append(f"simulation outcome={sim.state.outcome} steps={sim.state.step}")
    ok = sim.state.mission_done and sim.state.outcome != "RUNNING" and sim.state.step >= 10

    image_folder = resolve_project_path(config, config["paths"]["image_folder"])
    image_paths = sorted(p for p in image_folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    classifier = ImageClassifier(config)
    results = [classifier.classify(path, "mock") for path in image_paths]
    enemy_count = sum(1 for result in results if result.allegiance == "enemy")
    safe_count = sum(1 for result in results if result.threat_level == 1 and not result.should_spawn_in_simulation)
    messages.append(f"classifier images={len(results)} enemies={enemy_count} safe_non_targets={safe_count}")
    ok = ok and len(results) >= 5 and enemy_count >= 2 and safe_count >= 3

    if write_outputs:
        paths = write_reports(sim, config)
        messages.append(f"reports summary={paths['summary']}")
        ok = ok and paths["summary"].exists()

    return ok, messages
