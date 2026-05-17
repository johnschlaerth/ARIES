# ARIES MVP

ARIES, the Automated Robotic Integrated Effects System, is a local Python concept demo for AI-assisted orchestration of robotic ground effects nodes in a synthetic tactical environment.

This MVP does not control vehicles, radios, sensors, jammers, turrets, weapons, or any other hardware. Every effect is an abstract simulation state transition used to demonstrate prioritization, routing, assignment, and reporting logic.

## Quickstart

Use this path when you want the full Pygame GUI demo:

```bash
cd MVP/aries_mvp
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_tests.py
python run_demo.py
```

Mock mode is the default and requires no network connection or API key.

If `python3.11` is not available, Python 3.12 is also a good target. Avoid Python versions newer than the packages support; Pygame may not have wheels for very new interpreters.

For headless validation without Pygame, install the smaller dependency set:

```bash
cd MVP/aries_mvp
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-headless.txt
python run_tests.py
python run_headless.py --no-replay
python run_self_check.py
```

## Tutorial: First Successful Run

There are two normal ways to use the project:

- Headless path: best for verifying the simulator, classifier mock data, reports, replay files, and tests without a GUI.
- GUI path: best for the actual tactical-map demo. This requires Pygame and should be run with Python 3.11 or 3.12.

Start with the headless path if anything about Pygame or your Python version is uncertain.

1. Open a terminal at the challenge folder.
2. Enter the MVP project:

   ```bash
   cd MVP/aries_mvp
   ```

3. Create and activate a Python 3.11 or 3.12 virtual environment.

   macOS/Linux:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```

   Windows PowerShell:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies.

   For the full GUI demo:

   ```bash
   pip install -r requirements.txt
   ```

   For headless-only validation:

   ```bash
   pip install -r requirements-headless.txt
   ```

5. Run the deterministic testbench:

   ```bash
   python run_tests.py
   ```

   Expected success line:

   ```text
   passed
   ```

6. Run a complete headless mission and write reports. This does not require Pygame:

   ```bash
   python run_headless.py
   ```

   Expected output includes:

   ```text
   ARIES headless run complete: outcome=ALL_THREATS_DISABLED steps=52
   Mission report: ...
   Summary JSON: ...
   Replay JSON: ...
   ```

   The generated files are written under `outputs/reports/` and `outputs/replays/`.

7. Run the compact non-GUI readiness check:

   ```bash
   python run_self_check.py
   ```

   Expected output:

   ```text
   ARIES self-check passed
   ```

8. Run the classifier mock demo against the included placeholder JPEGs:

   ```bash
   python run_classifier.py --mode mock --folder data/images
   ```

   Expected behavior:

   - `enemy_drone.jpg` returns `enemy_drone` with high threat.
   - `enemy_ground_vehicle.jpg` returns `enemy_ground_vehicle`.
   - `friendly_soldier.jpg`, `puppy.jpg`, and `random_object.jpg` return safe low-threat classifications.

9. Run the classifier GUI visual test:

   ```bash
   python run_visual_tests.py --view classifier --mode mock
   ```

   Expected behavior: a Pygame window opens with each placeholder image and its classification. Press `Q` or `ESC` to quit.

10. Run the simulation GUI visual test:

   ```bash
   python run_visual_tests.py --view simulation
   ```

   Expected behavior: a Pygame tactical map opens and automatically steps through the default scenario. Press `Q` or `ESC` to quit.

11. Run the full ARIES demo:

   ```bash
   python run_demo.py
   ```

   The default scenario is paced for visual inspection: it should run long enough to watch assignments, movement, ISR classification, abstract effects, and disabled X markers before the mission report is written.

   The GUI starts paused by default. Press `SPACE` to run, `N` to step once, and `Q` or `ESC` to quit.

## Run Modes

- `mock`: deterministic offline mode using `data/mock_classifications.json`.
- `api`: optional OpenAI vision classification. It compresses images, validates JSON, caches results, and falls back safely.
- `replay`: loads saved replay frames from `outputs/replays/`.

To try API classification:

```bash
cp .env.example .env
# edit .env so it contains: OPENAI_API_KEY=your_key_here
python run_classifier.py --mode api --enable-api --folder data/images
```

The app automatically reads `.env` from either `MVP/aries_mvp/.env` or `MVP/.env`. Shell environment variables take precedence over `.env` values.

API mode is optional. If the API key is missing, the API call fails, or the model returns invalid JSON, the classifier falls back to cache/mock/safe unknown behavior instead of crashing.

To classify your own images, copy JPG or PNG files into `data/images/`, then run:

```bash
python run_classifier.py --mode mock --folder data/images
python run_classifier.py --mode api --enable-api --folder data/images
```

## Placeholder Images

The `data/images/` folder includes simple placeholder JPEGs:

- `enemy_drone.jpg`
- `enemy_ground_vehicle.jpg`
- `friendly_soldier.jpg`
- `puppy.jpg`
- `random_object.jpg`

These are intentionally not AI-generated. They exist so the mock classifier, API plumbing, image compression, caching, and GUI visual testbench can run immediately. Replace or add real local images when you want meaningful API classification.

## Controls

- `SPACE`: pause or resume
- `N`: step one timestep
- `R`: reset scenario
- `F`: toggle fast mode
- `V`: toggle vectors
- `P`: toggle paths
- `S`: save screenshot
- `Q` or `ESC`: quit

In `run_demo.py`, the simulation starts paused unless `config/aries_config.json` is changed. Press `SPACE` to begin.

## Symbols

- Enemy drone: red downward triangle
- Enemy ground vehicle: red diamond
- Enemy EW: red circle with RF rings
- Enemy unknown: red question-mark diamond
- Friendly COMMS: blue relay node
- Friendly EW: cyan RF node
- Friendly ISR: green sensor node
- Friendly C-UAS: yellow turret
- Friendly EFFECT: green square/cross
- Disabled/dead entities: X marker retained on the map
- Neutral/non-threat: white or gray simple markers

## Scoring

The central battle manager computes global threat scores from threat level, objective proximity, friendly proximity, speed, payload relevance, confidence, and network threat.

Each friendly node also computes a local preference from threat level, proximity, payload match, path accessibility, central recommendation, risk, and cooldown state.

Neutral, friendly, civilian, animal, and non-threat entities are never selected as effect targets.

## Reports

At mission end, reports are written to `outputs/reports/`:

- mission report TXT
- entity CSV
- event CSV
- summary JSON

For machines without Pygame, use:

```bash
python run_headless.py
```

That command runs the configured scenario to completion, writes reports, and saves a replay JSON unless `--no-replay` is passed.

Inspect a saved replay:

```bash
python run_replay.py outputs/replays/replay_YYYYMMDD_HHMMSS.json
```

For a quick readiness check that exercises simulation and mock classifier behavior without opening a GUI:

```bash
python run_self_check.py
```

To also write reports during the check:

```bash
python run_self_check.py --write-reports
```

## Scenarios

Scenario JSON files live in `scenarios/`. The default demo includes COMMS, EW, ISR, C-UAS, EFFECT, drones, ground threats, enemy EW, an unknown contact, and a neutral marker.

To run a different scenario headlessly:

```bash
python run_headless.py --scenario scenarios/simple_test_scenario.json
```

The basic scenario builder can be launched with:

```bash
python -m aries.scenario_builder
```

Scenario builder controls:

- `1`: friendly COMMS
- `2`: friendly EW
- `3`: friendly ISR
- `4`: friendly C-UAS
- `5`: friendly EFFECT
- `6`: enemy drone
- `7`: enemy ground vehicle
- `8`: enemy EW
- `9`: unknown contact
- `0`: neutral/non-threat
- mouse click: place selected entity
- `S`: save to `scenarios/builder_scenario.json`
- `ESC`: quit

## Tests

```bash
python run_tests.py
pytest tests/
```

The tests are deterministic and pass without an API key.

The strongest non-GUI readiness sequence is:

```bash
python run_tests.py
python run_self_check.py
python run_headless.py --no-replay
```

## GUI Visual Tests

Classifier visual test:

```bash
python run_visual_tests.py --view classifier --mode mock
```

Optional API classifier visual test:

```bash
python run_visual_tests.py --view classifier --mode api --enable-api
```

Simulation visual test:

```bash
python run_visual_tests.py --view simulation
```

Auto-close after 300 frames:

```bash
python run_visual_tests.py --view simulation --frames 300
```

## Troubleshooting

- `python: command not found`: use `python3.11`, `python3.12`, or activate the virtual environment.
- Pygame build fails looking for `SDL.h`: use Python 3.11 or 3.12 so pip can install a prebuilt Pygame wheel.
- API mode returns mock results: verify `.env` contains `OPENAI_API_KEY=...`, pass `--enable-api`, and confirm `config/aries_config.json` has a valid model name.
- No images found: put JPG or PNG files in `data/images/` or use `--folder path/to/images`.
- Reports are missing: let the mission end or quit `run_demo.py`; reports are written to `outputs/reports/`.
- GUI dependencies are unavailable: run `python run_headless.py` to validate simulation, reports, and replay without Pygame.
- Need a fast readiness gate: run `python run_self_check.py`.
