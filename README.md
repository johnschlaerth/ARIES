# ARIES MVP

**Automated Robotic Integrated Effects System** — AI-assisted mission orchestration for robotic ground effects nodes.

ARIES is the software intelligence layer of a larger system concept combining Polymath Robotics vehicle automation, Allen Control Systems counter-UAS payloads, and L3Harris tactical communications (RF-9820S, Wraith Shield), ISR, EW, and C2 mission systems into a distributed, attritable robotic ground effects architecture.

This MVP is a local Python simulation. It does not connect to real vehicles, radios, sensors, jammers, turrets, or weapons. Every effect is an abstract simulation state transition used to demonstrate classification, prioritization, terrain-aware routing, effect assignment, and mission reporting logic.

---

## Quickstart

```bash
cd MVP/ARIES
python3.11 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_tests.py             # 49 deterministic tests, no API key needed
python run_launcher.py          # Mission Control GUI — start here for demos
```

For headless validation without Pygame:

```bash
pip install -r requirements-headless.txt
python run_self_check.py
python run_headless.py --no-replay
```

---

## Entry Points

| Command | Description |
|---|---|
| `python run_launcher.py` | **Mission Control** — configure and launch everything from one GUI |
| `python run_demo.py` | Tactical simulation GUI directly |
| `python run_classifier_gui.py` | Live image classifier with step-by-step visualization |
| `python run_classifier.py` | Batch classifier (CLI) |
| `python -m aries.scenario_builder` | Drag-and-drop scenario authoring tool |
| `python run_headless.py` | Full mission run, no Pygame, writes reports |
| `python run_self_check.py` | Fast non-GUI readiness gate |
| `python run_tests.py` | Full pytest testbench |
| `python run_replay.py <file>` | Inspect a saved replay JSON |

---

## Mission Control Launcher

`run_launcher.py` is the primary demo entry point. It provides a keyboard-navigated configuration panel where you can set:

- **Scenario** — min/max enemies, neutrals, map dimensions, fixed or random terrain seed
- **Simulation** — start paused, max steps, show paths/vectors/effect ranges
- **Classifier** — run a fresh classification pass before launch, API vs mock mode, image count

Keys: `↑↓` navigate, `←→` or `+/-` change values, `SPACE` launch simulation, `C` launch classifier GUI, `B` launch scenario builder, `Q` quit.

When "Run Classifier Before Launch" is enabled, pressing `SPACE` runs the classifier first and auto-launches the simulation when the classification session completes.

---

## Live Image Classifier

`run_classifier_gui.py` classifies a random sample of images from `data/images/` using the OpenAI vision API and displays each result live as it arrives.

```bash
python run_classifier_gui.py            # API mode, 4-10 random images
python run_classifier_gui.py --count 5 # classify exactly 5
python run_classifier_gui.py --mock    # instant mock mode, no key needed
```

**Controls:** Press `N` or `SPACE` to advance to the next image. `Q` or `ESC` to quit.

While classifying, the current image fills the left panel. An animated loading bar shows elapsed API response time. Results accumulate on the right panel with confidence bars and threat level indicators.

When all images are classified, the results are written to `config/classified_entities.json`. All future simulation runs will automatically inject those classified entities into the scenario as enemy, neutral, or unknown contacts — until the classifier is run again.

**Friend-or-foe discrimination:** The API prompt explicitly instructs the model to classify US/NATO equipment as `allegiance: friendly` (excluded from the threat queue) and adversary equipment as `allegiance: enemy`. FPV drones and loitering munitions return threat levels 7–9. Unknown military contacts are held as `unknown_contact` for ISR clarification before any engagement consideration.

### API setup

```bash
# Place key in MVP/.env or MVP/ARIES/.env
echo "OPENAI_API_KEY=your_key_here" > .env
python run_classifier_gui.py
```

The app loads the key automatically. Shell environment variables take precedence over `.env` values. API mode falls back gracefully to cached results or mock mode if the key is missing or the call fails.

---

## Tactical Simulation

### Symbol reference

| Symbol | Meaning |
|---|---|
| Red downward triangle | Enemy drone (air, ignores terrain) |
| Red diamond | Enemy ground vehicle (terrain-aware routing) |
| Red circle with rings | Enemy EW node (degrades friendly network radius) |
| Red question-mark diamond | Unknown contact (awaits ISR classification) |
| Blue node-circle | ARIES-COMMS relay (extends L3Harris mesh coverage) |
| Cyan circle with rings | ARIES-EW (suppresses enemy movement and electronics) |
| Green sensor arc | ARIES-ISR (improves classification confidence) |
| Yellow turret | ARIES-CUAS (counter-drone, limited magazine) |
| Green square/cross | ARIES-EFFECT (close-effects node, ground targets) |
| X marker | Disabled / killed entity (remains on map) |

### Controls

| Key | Action |
|---|---|
| `SPACE` | Pause / resume |
| `N` | Step one timestep |
| `R` | Reset scenario |
| `F` | Toggle fast mode (5× speed) |
| `V` | Toggle velocity vectors |
| `P` | Toggle planned paths |
| `S` | Save screenshot |
| `B` | Print builder/classifier launch commands to terminal |
| `Q` / `ESC` | Quit |

### Scenario generation

Each run generates a unique tactical scenario with random terrain. Friendlies spawn on the left, enemies on the right.

```bash
python run_demo.py                         # random scenario, random terrain
python run_demo.py --seed 42               # reproducible scenario
python run_demo.py --scenario scenarios/demo_scenario.json  # fixed scenario
python run_headless.py --random --seed 123 --no-replay
```

If `config/classified_entities.json` exists (produced by the classifier), spawnable entities from that session are automatically added to the enemy/neutral force.

---

## Decision Logic

### Two-tier architecture

**Central battle manager** — runs globally each timestep, produces a ranked threat table and recommended assignments:

```
global_score = 4.0 × threat_level
             + 20.0 × objective_proximity_norm
             + 10.0 × friendly_proximity_norm
             + 10.0 × speed_norm
             + 10.0 × payload_relevance_norm
             +  5.0 × confidence_norm
             +  5.0 × network_threat_norm
```

**Local vehicle agent** — each ARIES node runs its own scoring independently, enabling degraded-comms operation:

```
local_score = 3.0 × threat_level
            + 25.0 × proximity_norm
            + 20.0 × payload_match
            + 10.0 × path_accessibility
            + 10.0 × central_manager_bonus
            - 15.0 × risk_penalty
            - 10.0 × cooldown_penalty
```

When the radio link is degraded (simulated by enemy EW reducing the COMMS network radius by 35%), units lose the `central_manager_bonus` but continue operating on local scoring.

### Payload matching

| ARIES node | Strong against | Weak against |
|---|---|---|
| EW | Drones, enemy EW, unknown electronics | Ground vehicles, infantry |
| ISR | Unknown contacts, low-confidence entities | N/A (sensor only) |
| C-UAS | Enemy drones (100% match) | Ground targets (10% match) |
| EFFECT | Ground vehicles, fixed nodes | Fast drones |
| COMMS | Moves to support network geometry | Not an effector |

### Bidirectional combat

Enemy units engage friendly ARIES nodes when they enter their attack envelope:

- Enemy drones: range 110, attack probability 22%, cooldown 4 steps
- Enemy ground vehicles: range 90, attack probability 18%, cooldown 5 steps
- Enemy EW nodes: range 180, jams all friendlies in range for 6 steps, cooldown 8 steps

Friendly units have 100 HP. Each hit deals `threat_level × 3` damage. Damaged units show a health bar and shift color (green → amber → orange-red). Units at 0 HP are eliminated and remain on the map as X marks.

Neutral, friendly, civilian, animal, and non-threat entities are never selected as effect targets at any layer.

---

## Terrain

Terrain is generated procedurally from a random seed each new scenario using a sum of Gaussian hills. Ground entities route around high-cost terrain via A* pathfinding weighted by elevation and slope. Air entities (drones) fly direct regardless of terrain. The seed is logged in the scenario file and in mission reports, making any run reproducible.

---

## Scenario Builder

The drag-and-drop scenario builder lets you manually place entities on the map:

```bash
python -m aries.scenario_builder
```

**Keys:** `1`–`0` select entity type, mouse click places, drag to reposition, `R` random setup, `S` save, `L` load, `C` clear, `ESC` quit.

If `config/classified_entities.json` exists, a **Classified Entities** panel appears on the right. Click an entry to select it, then click the map to place it at that position with its real classification identity.

Saved scenarios live in `scenarios/builder_scenario.json`:

```bash
python run_demo.py --scenario scenarios/builder_scenario.json
```

---

## Adding Real Images

Place JPG or PNG files in `data/images/`, then run the classifier:

```bash
python run_classifier_gui.py --count 6    # classify 6 random images from the folder
```

The folder already contains placeholder images for mock-mode testing. Real military and threat imagery can be added alongside them. AVIF, WEBP, and JXL formats are skipped (PIL compatibility); use JPG or PNG.

---

## Run Modes

| Mode | Description |
|---|---|
| `mock` | Deterministic offline mode using `data/mock_classifications.json`. No API key required. Default for all tests and headless runs. |
| `api` | OpenAI GPT-4o-mini vision classification. Compresses images, validates JSON, caches results, falls back to mock on failure. |
| Replay | Load a saved replay JSON for inspection or screen recording. |

---

## Reports

At mission end, reports are written to `outputs/reports/`:

- `mission_report_TIMESTAMP.txt` — human-readable summary
- `mission_entities_TIMESTAMP.csv` — final entity state table
- `mission_events_TIMESTAMP.csv` — full timestamped event log
- `mission_summary_TIMESTAMP.json` — structured summary for downstream processing

Report fields include: scenario name, seed, outcome, enemies neutralized, friendlies lost, network uptime %, average threat response time, top threats by global score, and complete event log.

```bash
python run_headless.py                     # run and write reports
python run_replay.py outputs/replays/replay_*.json   # inspect a saved replay
```

---

## Tests

```bash
python run_tests.py      # 49 deterministic pytest tests
python run_self_check.py # fast non-GUI readiness gate
```

All tests pass without an API key or Pygame display. The test suite covers classification, scoring, pathfinding, effects, simulation stepping, report writing, scenario loading, and entry point validation.

The strongest pre-demo readiness sequence:

```bash
python run_tests.py && python run_self_check.py && python run_headless.py --no-replay
```

---

## Troubleshooting

**`python: command not found`** — use `python3.11`, `python3.12`, or activate the venv.

**Pygame build fails** — use Python 3.11 or 3.12 so pip can install a prebuilt Pygame wheel.

**Classifier returns all unknowns** — check that `OPENAI_API_KEY` is set in `.env` or the shell environment. Run `python run_classifier_gui.py --mock` to verify the UI without the API.

**Simulation ends in a few steps** — if classified entities are in `config/classified_entities.json`, ensure you are not loading a stale file from a previous run with different map dimensions. Delete or regenerate it.

**No images found** — put JPG or PNG files in `data/images/`.

**Reports missing** — let the mission reach an end condition, or quit with `Q`; reports are written on exit.

**Need a non-GUI validation path** — run `python run_headless.py` or `python run_self_check.py`.

---

## Effects Disclaimer

All effects in this simulation — suppression, classification improvement, network relay, counter-UAS neutralization, and close effects — are abstract simulation state transitions. This software does not model real jamming parameters, real weapon physics, real fire-control logic, real munition behavior, or any classified performance values. It is a concept demonstration only.
