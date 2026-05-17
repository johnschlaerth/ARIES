"""Launch the ARIES MVP Pygame demo."""

from __future__ import annotations

from aries.config_loader import load_config, load_default_scenario
from aries.gui_controls import GuiControls
from aries.renderer import Renderer
from aries.replay import save_replay
from aries.report_writer import write_reports
from aries.simulation import Simulation


def main() -> None:
    try:
        import pygame
    except ImportError as exc:
        raise SystemExit(
            "Pygame is required for the GUI demo. Install with `pip install -r requirements.txt` "
            "inside a Python 3.11 or 3.12 virtual environment. For non-GUI validation, run "
            "`python run_headless.py --no-replay` or `python run_self_check.py`."
        ) from exc

    config = load_config()
    scenario = load_default_scenario(config)
    sim = Simulation(scenario, config)
    controls = GuiControls()
    renderer = Renderer(config, sim)
    clock = pygame.time.Clock()
    reports_written = False

    while not controls.quit_requested:
        for event in pygame.event.get():
            controls.handle_event(event, sim)
        steps = 5 if controls.fast_mode and not sim.state.paused else 1
        if not sim.state.paused or controls.single_step:
            for _ in range(steps):
                sim.step()
                if sim.state.mission_done:
                    break
            controls.single_step = False
        renderer.render(controls)
        if controls.save_screenshot:
            renderer.save_screenshot()
            controls.save_screenshot = False
        if sim.state.mission_done and not reports_written and config["simulation"].get("output_reports", True):
            write_reports(sim, config)
            save_replay(sim, config)
            reports_written = True
        clock.tick(int(config["display"].get("fps", 30)))
    if not reports_written and config["simulation"].get("output_reports", True):
        write_reports(sim, config)
        save_replay(sim, config)
    pygame.quit()


if __name__ == "__main__":
    main()
