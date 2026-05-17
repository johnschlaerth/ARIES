"""Interactive visual testbenches for demo confidence checks."""

from __future__ import annotations

import argparse
from pathlib import Path

from .classifier import ImageClassifier
from .config_loader import load_config, load_default_scenario, resolve_project_path
from .renderer import Renderer
from .simulation import Simulation


def run_classifier_view(config: dict, mode: str, enable_api: bool) -> None:
    """Display local images with their classifier outputs in a Pygame grid."""

    try:
        import pygame
    except ImportError as exc:
        raise SystemExit("Pygame is required for visual tests. Install requirements in Python 3.11/3.12.") from exc

    if enable_api:
        config["openai"]["enabled"] = True
        config["run_mode"] = "api"
    classifier = ImageClassifier(config)
    folder = resolve_project_path(config, config["paths"]["image_folder"])
    image_paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    results = [(path, classifier.classify(path, mode)) for path in image_paths]

    pygame.init()
    screen = pygame.display.set_mode((1200, 760))
    pygame.display.set_caption("ARIES Classifier Visual Testbench")
    font = pygame.font.SysFont("courier", 17)
    small = pygame.font.SysFont("courier", 14)
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in {pygame.K_ESCAPE, pygame.K_q}):
                running = False
        screen.fill((0, 0, 0))
        screen.blit(font.render("ARIES CLASSIFIER VISUAL TESTBENCH  |  Q/ESC quit", True, (0, 220, 80)), (18, 14))
        if not results:
            screen.blit(font.render("No images found in data/images.", True, (240, 220, 60)), (18, 60))
        for idx, (path, result) in enumerate(results):
            col = idx % 2
            row = idx // 2
            x = 22 + col * 575
            y = 58 + row * 132
            pygame.draw.rect(screen, (0, 90, 50), (x, y, 540, 112), 1)
            _draw_image_or_box(pygame, screen, path, (x + 10, y + 12))
            color = (240, 50, 50) if result.allegiance == "enemy" else (80, 220, 120) if result.allegiance == "friendly" else (230, 230, 230)
            lines = [
                f"{path.name}",
                f"{result.name} | {result.allegiance} | {result.entity_type}",
                f"threat={result.threat_level} confidence={result.confidence:.2f} source={result.source}",
                f"spawn={result.should_spawn_in_simulation}",
            ]
            for line_no, line in enumerate(lines):
                screen.blit(small.render(line[:72], True, color if line_no == 1 else (220, 220, 220)), (x + 130, y + 12 + line_no * 22))
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()


def _draw_image_or_box(pygame, screen, path: Path, pos: tuple[int, int]) -> None:
    try:
        image = pygame.image.load(str(path))
        image = pygame.transform.smoothscale(image, (96, 72))
        screen.blit(image, pos)
    except Exception:
        pygame.draw.rect(screen, (120, 120, 120), (pos[0], pos[1], 96, 72), 1)


def run_simulation_view(config: dict, frames: int | None) -> None:
    """Run the main renderer with automatic stepping for visual inspection."""

    try:
        import pygame
    except ImportError as exc:
        raise SystemExit("Pygame is required for visual tests. Install requirements in Python 3.11/3.12.") from exc

    scenario = load_default_scenario(config)
    sim = Simulation(scenario, config)
    sim.state.paused = False
    renderer = Renderer(config, sim)
    clock = pygame.time.Clock()
    count = 0
    running = True

    class Controls:
        show_vectors = True
        show_paths = True

    controls = Controls()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in {pygame.K_ESCAPE, pygame.K_q}):
                running = False
        if not sim.state.mission_done:
            sim.step()
        renderer.render(controls)
        count += 1
        if frames is not None and count >= frames:
            running = False
        clock.tick(int(config["display"].get("fps", 30)))
    pygame.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ARIES GUI visual testbenches.")
    parser.add_argument("--view", choices=["classifier", "simulation"], default="classifier")
    parser.add_argument("--mode", choices=["mock", "api"], default="mock")
    parser.add_argument("--enable-api", action="store_true")
    parser.add_argument("--frames", type=int, default=None, help="Auto-close simulation view after N frames.")
    args = parser.parse_args()
    config = load_config()
    if args.view == "classifier":
        run_classifier_view(config, args.mode, args.enable_api)
    else:
        run_simulation_view(config, args.frames)


if __name__ == "__main__":
    main()
