"""ARIES Mission Control — master launcher and config GUI.

Navigate settings with ↑/↓. Change values with ←/→ or +/-.
Launch the simulation with SPACE, classifier with C, builder with B.
Config is saved to aries_config.json before each launch.

Usage:
    python run_launcher.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

# ── Colors (retro green-on-black palette) ─────────────────────────────────────
BG        = (4,   10,  4)
PANEL_BG  = (0,   18,  8)
HEADER_BG = (0,   28,  12)
GREEN     = (0,   220, 80)
DIM_GREEN = (0,   60,  28)
BRIGHT    = (140, 255, 160)
YELLOW    = (245, 220, 60)
CYAN      = (0,   220, 230)
WHITE     = (220, 220, 220)
GRAY      = (90,  90,  90)
RED       = (240, 40,  40)
ORANGE    = (255, 150, 30)
SEL_BG    = (0,   45,  20)

W, H = 1100, 740


# ── Setting descriptors ────────────────────────────────────────────────────────

def _setting(key: str, label: str, kind: str, **kw) -> dict:
    return {"key": key, "label": label, "kind": kind, **kw}


SETTINGS = [
    # ── SCENARIO ──────────────────────────────────────────────────────────────
    {"kind": "header", "label": "SCENARIO"},
    _setting("scenario_generation.min_enemies",  "Min Enemies",      "int",    min=1,  max=20, step=1),
    _setting("scenario_generation.max_enemies",  "Max Enemies",      "int",    min=1,  max=30, step=1),
    _setting("scenario_generation.max_neutrals", "Max Neutrals",     "int",    min=0,  max=10, step=1),
    _setting("scenario_generation.map_width",    "Map Width",        "int",    min=600, max=2000, step=50),
    _setting("scenario_generation.map_height",   "Map Height",       "int",    min=400, max=1400, step=50),
    _setting("_use_fixed_seed",                  "Fixed Seed",       "bool"),
    _setting("simulation.seed",                  "Seed Value",       "int",    min=1,  max=999_999_999, step=1,
             note="(only used when Fixed Seed is ON)"),
    _setting("scenario_generation.min_enemies",  "Include Classified Entities",  "note",
             note="Run classifier GUI separately to populate"),

    # ── SIMULATION ────────────────────────────────────────────────────────────
    {"kind": "header", "label": "SIMULATION"},
    _setting("simulation.start_paused",          "Start Paused",     "bool"),
    _setting("simulation.max_steps",             "Max Steps",        "int",    min=60, max=3000, step=60),
    _setting("display.show_paths",               "Show Paths",       "bool"),
    _setting("display.show_vectors",             "Show Vectors",     "bool"),
    _setting("display.show_effect_ranges",       "Show Effect Ranges", "bool"),

    # ── CLASSIFIER ────────────────────────────────────────────────────────────
    {"kind": "header", "label": "CLASSIFIER"},
    _setting("_run_classifier",                  "Run Classifier Before Launch", "bool"),
    _setting("_classifier_mode",                 "Classifier Mode",  "choice", choices=["api", "mock"]),
    _setting("_classifier_count",                "Image Count",      "int",    min=2,  max=15, step=1),
]

# Keys that start with _ are local-only (not written to config)
LOCAL_KEYS = {"_use_fixed_seed", "_run_classifier", "_classifier_mode", "_classifier_count"}


# ── Config helpers ─────────────────────────────────────────────────────────────

def _get(cfg: dict, dotkey: str) -> Any:
    parts = dotkey.split(".")
    node = cfg
    for p in parts:
        if not isinstance(node, dict) or p not in node:
            return None
        node = node[p]
    return node


def _set(cfg: dict, dotkey: str, value: Any) -> None:
    parts = dotkey.split(".")
    node = cfg
    for p in parts[:-1]:
        node = node.setdefault(p, {})
    node[parts[-1]] = value


def load_config_raw(root: Path) -> dict:
    path = root / "config" / "aries_config.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config_raw(root: Path, cfg: dict) -> None:
    path = root / "config" / "aries_config.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def init_values(cfg: dict) -> dict:
    """Pull current config values into the settings value dict."""
    vals: dict[str, Any] = {}
    for s in SETTINGS:
        if s["kind"] in ("header", "note"):
            continue
        key = s["key"]
        if key in LOCAL_KEYS:
            if key == "_use_fixed_seed":
                vals[key] = cfg.get("scenario_generation", {}).get("seed") is not None
            elif key == "_run_classifier":
                vals[key] = False
            elif key == "_classifier_mode":
                vals[key] = cfg.get("run_mode", "api")
            elif key == "_classifier_count":
                vals[key] = 6
        else:
            v = _get(cfg, key)
            vals[key] = v if v is not None else 0
    return vals


def apply_values(cfg: dict, vals: dict) -> dict:
    """Write values back into a config copy, ready to save."""
    out = deepcopy(cfg)
    for key, val in vals.items():
        if key in LOCAL_KEYS:
            continue
        _set(out, key, val)
    # Fixed seed logic
    if vals.get("_use_fixed_seed"):
        _set(out, "scenario_generation.seed", vals.get("simulation.seed", 42))
        _set(out, "scenario_generation.enabled", True)
    else:
        _set(out, "scenario_generation.seed", None)
        _set(out, "scenario_generation.enabled", True)
    return out


# ── Navigable items (skipping headers) ────────────────────────────────────────

def navigable(settings: list) -> list[int]:
    return [i for i, s in enumerate(settings) if s["kind"] not in ("header", "note")]


# ── Value mutation ─────────────────────────────────────────────────────────────

def adjust(s: dict, vals: dict, delta: int) -> None:
    key = s["key"]
    kind = s["kind"]
    if kind == "bool":
        vals[key] = not vals[key]
    elif kind == "int":
        step = s.get("step", 1)
        vals[key] = max(s.get("min", 0), min(s.get("max", 9999), vals[key] + delta * step))
    elif kind == "choice":
        choices = s["choices"]
        idx = choices.index(vals[key]) if vals[key] in choices else 0
        vals[key] = choices[(idx + delta) % len(choices)]


# ── Drawing ────────────────────────────────────────────────────────────────────

def draw_value(s: dict, vals: dict) -> str:
    key = s["key"]
    kind = s["kind"]
    v = vals.get(key)
    if kind == "bool":
        return "ON" if v else "OFF"
    if kind == "choice":
        return str(v).upper()
    if kind == "int":
        return str(v)
    return ""


def draw_screen(
    screen, pygame, font, small, tiny,
    sel_nav_idx: int, nav: list[int],
    vals: dict, proc_state: str, root: Path,
) -> None:
    screen.fill(BG)

    # ── Header bar ─────────────────────────────────────────────────────────────
    pygame.draw.rect(screen, HEADER_BG, (0, 0, W, 48))
    screen.blit(font.render("ARIES  MISSION CONTROL", True, GREEN), (14, 12))
    classified_path = root / "config" / "classified_entities.json"
    cls_label = "CLASSIFIED CONFIG: LOADED" if classified_path.exists() else "CLASSIFIED CONFIG: none (run classifier)"
    cls_color = CYAN if classified_path.exists() else GRAY
    screen.blit(small.render(cls_label, True, cls_color), (W - 340, 16))

    # ── Left settings panel ────────────────────────────────────────────────────
    PANEL_W = 620
    pygame.draw.rect(screen, PANEL_BG, (0, 48, PANEL_W, H - 48))

    y = 62
    row_h = 26
    sel_global = nav[sel_nav_idx] if nav else -1

    for i, s in enumerate(SETTINGS):
        kind = s["kind"]

        if kind == "header":
            pygame.draw.line(screen, DIM_GREEN, (10, y + 2), (PANEL_W - 10, y + 2), 1)
            screen.blit(small.render(s["label"], True, YELLOW), (14, y + 4))
            y += 22
            continue

        if kind == "note":
            screen.blit(tiny.render(s.get("note", ""), True, GRAY), (28, y + 6))
            y += row_h - 4
            continue

        is_sel = (i == sel_global)
        if is_sel:
            pygame.draw.rect(screen, SEL_BG, (2, y, PANEL_W - 4, row_h - 2), border_radius=3)

        label_color = BRIGHT if is_sel else WHITE
        val_str = draw_value(s, vals)

        # Dim seed value when fixed seed is OFF
        if s["key"] == "simulation.seed" and not vals.get("_use_fixed_seed"):
            label_color = GRAY
            val_str = f"{val_str}  (fixed seed OFF)"

        screen.blit(small.render(s["label"], True, label_color), (28, y + 5))

        # Value with brackets, colored by type
        val_color = CYAN if s["kind"] == "bool" and vals.get(s["key"]) else GREEN if s["kind"] == "bool" else YELLOW
        if s["kind"] == "bool" and not vals.get(s["key"]):
            val_color = GRAY
        screen.blit(small.render(f"[ {val_str} ]", True, val_color), (PANEL_W - 120, y + 5))

        if is_sel:
            screen.blit(tiny.render("← → or +/- to change", True, DIM_GREEN), (28, y + row_h - 8))

        y += row_h

    # ── Right info panel ───────────────────────────────────────────────────────
    rx = PANEL_W + 12
    pygame.draw.rect(screen, PANEL_BG, (PANEL_W + 2, 48, W - PANEL_W - 2, H - 48))
    pygame.draw.line(screen, DIM_GREEN, (PANEL_W + 1, 48), (PANEL_W + 1, H), 1)

    screen.blit(small.render("LAUNCH OPTIONS", True, YELLOW), (rx, 62))
    pygame.draw.line(screen, DIM_GREEN, (rx, 80), (W - 10, 80), 1)

    launches = [
        ("SPACE", "Launch Simulation",   GREEN),
        ("C",     "Launch Classifier GUI", CYAN),
        ("B",     "Launch Scenario Builder", CYAN),
        ("Q",     "Quit",                 GRAY),
    ]
    ly = 88
    for key, label, color in launches:
        screen.blit(small.render(f"  [{key}]  {label}", True, color), (rx, ly))
        ly += 24

    # Status box
    ly += 16
    pygame.draw.line(screen, DIM_GREEN, (rx, ly), (W - 10, ly), 1)
    ly += 8
    screen.blit(small.render("STATUS", True, YELLOW), (rx, ly))
    ly += 20
    if proc_state == "idle":
        screen.blit(small.render("Ready", True, GREEN), (rx, ly))
    elif proc_state == "classifier_running":
        screen.blit(small.render("Classifier running...", True, CYAN), (rx, ly))
        screen.blit(small.render("Sim will auto-launch when done", True, GRAY), (rx, ly + 18))
    elif proc_state == "sim_launching":
        screen.blit(small.render("Simulation launching...", True, YELLOW), (rx, ly))
    elif proc_state == "tool_running":
        screen.blit(small.render("External tool running", True, CYAN), (rx, ly))

    # Quick config summary
    ly += 60
    pygame.draw.line(screen, DIM_GREEN, (rx, ly), (W - 10, ly), 1)
    ly += 8
    screen.blit(small.render("CURRENT CONFIG SUMMARY", True, YELLOW), (rx, ly))
    ly += 20
    summary = [
        f"Enemies: {vals.get('scenario_generation.min_enemies',5)}-{vals.get('scenario_generation.max_enemies',8)}",
        f"Map: {vals.get('scenario_generation.map_width',1000)}x{vals.get('scenario_generation.map_height',700)}",
        f"Max Steps: {vals.get('simulation.max_steps',600)}",
        f"Seed: {'fixed '+str(vals.get('simulation.seed')) if vals.get('_use_fixed_seed') else 'random'}",
        f"Start Paused: {'yes' if vals.get('simulation.start_paused') else 'no'}",
        f"Classifier: {'yes ('+vals.get('_classifier_mode','api')+')' if vals.get('_run_classifier') else 'skip'}",
    ]
    for line in summary:
        screen.blit(tiny.render(line, True, WHITE), (rx, ly))
        ly += 16

    # ── Bottom key hint bar ────────────────────────────────────────────────────
    pygame.draw.rect(screen, HEADER_BG, (0, H - 36, W, 36))
    screen.blit(tiny.render(
        "  ↑/↓ navigate    ←/→  or  +/-  change value    SPACE launch sim    C classifier    B builder    Q quit",
        True, GRAY), (10, H - 22))

    pygame.display.flip()


# ── Subprocess management ──────────────────────────────────────────────────────

def launch(root: Path, args: list[str]) -> subprocess.Popen:
    return subprocess.Popen([sys.executable] + args, cwd=str(root))


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        import pygame
    except ImportError:
        sys.exit("Pygame required: pip install -r requirements.txt")

    root = Path(__file__).resolve().parent
    cfg = load_config_raw(root)
    vals = init_values(cfg)

    nav = navigable(SETTINGS)
    sel = 0  # index into nav

    proc_state = "idle"
    active_proc: subprocess.Popen | None = None
    pending_sim_after_classifier = False

    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("ARIES Mission Control")
    font  = pygame.font.SysFont("courier", 18)
    small = pygame.font.SysFont("courier", 15)
    tiny  = pygame.font.SysFont("courier", 13)
    clock = pygame.time.Clock()

    running = True
    while running:
        # ── Poll active subprocess ─────────────────────────────────────────────
        if active_proc is not None:
            ret = active_proc.poll()
            if ret is not None:
                active_proc = None
                if pending_sim_after_classifier:
                    pending_sim_after_classifier = False
                    _do_launch_sim(root, cfg, vals)
                    proc_state = "sim_launching"
                else:
                    proc_state = "idle"

        # ── Events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                key = event.key

                if key in {pygame.K_q, pygame.K_ESCAPE}:
                    running = False

                elif key == pygame.K_UP:
                    sel = (sel - 1) % len(nav)

                elif key == pygame.K_DOWN:
                    sel = (sel + 1) % len(nav)

                elif key in {pygame.K_LEFT, pygame.K_MINUS}:
                    adjust(SETTINGS[nav[sel]], vals, -1)

                elif key in {pygame.K_RIGHT, pygame.K_PLUS, pygame.K_EQUALS}:
                    adjust(SETTINGS[nav[sel]], vals, +1)

                elif key == pygame.K_SPACE:
                    if proc_state == "idle":
                        if vals.get("_run_classifier"):
                            active_proc = _do_launch_classifier(root, vals)
                            proc_state = "classifier_running"
                            pending_sim_after_classifier = True
                        else:
                            _do_launch_sim(root, cfg, vals)
                            proc_state = "sim_launching"

                elif key == pygame.K_c:
                    if proc_state == "idle":
                        active_proc = _do_launch_classifier(root, vals)
                        proc_state = "tool_running"
                        pending_sim_after_classifier = False

                elif key == pygame.K_b:
                    if proc_state == "idle":
                        active_proc = subprocess.Popen(
                            [sys.executable, "-m", "aries.scenario_builder"], cwd=str(root))
                        proc_state = "tool_running"

        draw_screen(screen, pygame, font, small, tiny, sel, nav, vals, proc_state, root)
        clock.tick(30)

    pygame.quit()


def _do_launch_sim(root: Path, cfg: dict, vals: dict) -> None:
    updated = apply_values(cfg, vals)
    save_config_raw(root, updated)
    args = ["run_demo.py"]
    if not vals.get("_use_fixed_seed"):
        args.append("--random")
    else:
        args += ["--seed", str(vals.get("simulation.seed", 42))]
    # Launch and don't track — sim is its own window, launcher stays open
    subprocess.Popen([sys.executable] + args, cwd=str(root))


def _do_launch_classifier(root: Path, vals: dict) -> subprocess.Popen:
    args = ["run_classifier_gui.py", "--count", str(vals.get("_classifier_count", 6))]
    if vals.get("_classifier_mode") == "mock":
        args.append("--mock")
    return launch(root, args)


if __name__ == "__main__":
    main()
