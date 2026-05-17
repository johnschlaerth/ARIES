# AGENTS.md

## Mission Context

This project is the ARIES MVP: a local, deterministic Python simulator for demonstrating AI-assisted orchestration of robotic ground effects nodes. It is a concept demonstration only.

Do not add real vehicle control, radio control, jamming, weapon, munition, targeting, fire-control, or hardware integration logic. Effects must remain abstract state transitions inside the simulation.

## Containment Rule

All project work belongs under `MVP/aries_mvp/`. Do not modify files in the parent challenge directory.

## Architecture

- `run_demo.py`: launches the Pygame demo.
- `run_classifier.py`: classifies images in mock or optional API mode.
- `run_tests.py`: runs the deterministic pytest testbench.
- `run_visual_tests.py`: launches GUI visual testbenches for classifier and simulation inspection.
- `run_headless.py`: runs a complete mission without Pygame and writes reports/replay.
- `run_self_check.py`: compact non-GUI readiness gate for simulation and classifier behavior.
- `run_replay.py`: inspect saved replay JSON from terminal.
- `aries/models.py`: dataclasses and validation-friendly model helpers.
- `aries/config_loader.py`: config and scenario loading.
- `aries/terrain.py`: deterministic synthetic terrain and contour helpers.
- `aries/pathfinding.py`: ground A* and air direct paths.
- `aries/scoring.py`: payload matching, global scoring pieces, and network support.
- `aries/battle_manager.py`: global ranking and central assignments.
- `aries/local_agent.py`: per-friendly target selection and movement intent.
- `aries/effects.py`: abstract suppress/classify/relay/neutralize logic.
- `aries/simulation.py`: deterministic simulation state update loop.
- `aries/renderer.py`: Pygame tactical display.
- `aries/classifier.py`: mock/API/cached classification.
- `aries/report_writer.py`: mission reports.
- `aries/replay.py`: replay frame persistence.
- `aries/scenario_builder.py`: simple Pygame scenario authoring tool.
- `aries/visual_testbench.py`: classifier and simulation GUI confidence checks.
- `aries/self_check.py`: reusable non-GUI readiness check.

## Development Rules

- Mock mode must remain the most reliable path.
- Tests must not require an API key or Pygame display.
- Headless mission execution must keep working without pandas or Pygame imports.
- `requirements-headless.txt` must remain enough for tests, classifier mock/API plumbing, reports, and `run_headless.py`.
- When `simulation.record_replay` is false, the simulation must not accumulate replay frames in memory.
- `.env` files may live in either `MVP/aries_mvp/.env` or `MVP/.env`; shell environment variables win.
- Add comments for non-obvious behavior and safety boundaries.
- Preserve deterministic behavior by routing randomness through seeded RNGs.
- Keep external dependencies limited to `requirements.txt`.
- Never target neutral, friendly, civilian, animal, or non-threat entities in effect logic.

## Acceptance Checklist

- `python run_tests.py` passes.
- `python run_demo.py` launches mock mode.
- Pygame display shows terrain, entities, vectors, paths, legend, priority table, assignments, and event log.
- Dead/disabled entities remain visible as X.
- Reports are written at mission end.
- API classifier mode gracefully falls back to cache/mock/safe unknown.
- `python run_visual_tests.py --view classifier --mode mock` shows the included placeholder image classifications.
- `python run_headless.py` completes the default scenario and writes mission outputs.
- `python run_self_check.py` must pass before treating the MVP as demo-ready.
