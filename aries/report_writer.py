"""Mission report export."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from .config_loader import resolve_project_path
from .simulation import Simulation
from .utils import write_json


def write_reports(sim: Simulation, config: dict) -> dict[str, Path]:
    report_dir = resolve_project_path(config, config["paths"]["report_folder"])
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path = report_dir / f"mission_report_{stamp}.txt"
    entity_path = report_dir / f"mission_entities_{stamp}.csv"
    event_path = report_dir / f"mission_events_{stamp}.csv"
    summary_path = report_dir / f"mission_summary_{stamp}.json"

    enemies_neutralized = sum(1 for e in sim.enemies if e.disabled)
    enemies_remaining = sum(1 for e in sim.enemies if e.active)
    friendlies_disabled = sum(1 for f in sim.friendlies if not f.active)
    response_times = [
        e.neutralized_step - (e.first_seen_step or 0)
        for e in sim.enemies
        if e.neutralized_step is not None
    ]
    avg_response = sum(response_times) / len(response_times) if response_times else None
    network_uptime = (
        sum(sim.state.network_uptime_samples) / len(sim.state.network_uptime_samples) * 100.0
        if sim.state.network_uptime_samples
        else 0.0
    )

    _write_csv(entity_path, [entity.to_dict() for entity in sim.all_entities])
    _write_csv(event_path, [event.to_dict() for event in sim.state.events])
    summary = {
        "scenario_name": sim.scenario.scenario_name,
        "run_mode": config.get("run_mode", "mock"),
        "simulation_seed": config.get("simulation", {}).get("seed"),
        "total_timesteps": sim.state.step,
        "mission_outcome": sim.state.outcome,
        "enemies_neutralized": enemies_neutralized,
        "enemies_remaining": enemies_remaining,
        "friendlies_disabled": friendlies_disabled,
        "average_threat_response_time": avg_response,
        "network_uptime_percentage": round(network_uptime, 2),
        "top_threats": [
            {"id": e.id, "name": e.name, "score": e.priority_score_global}
            for e in sim.manager.priority_table[:5]
        ],
        "classification_note": "Mock mode is deterministic; API mode is optional and cached.",
    }
    write_json(summary_path, summary)

    lines = [
        "ARIES MVP Mission Report",
        f"Scenario: {sim.scenario.scenario_name}",
        f"Run mode: {config.get('run_mode', 'mock')}",
        f"Seed: {config.get('simulation', {}).get('seed')}",
        f"Timesteps: {sim.state.step}",
        f"Outcome: {sim.state.outcome}",
        f"Enemies neutralized: {enemies_neutralized}",
        f"Enemies remaining: {enemies_remaining}",
        f"Friendlies disabled: {friendlies_disabled}",
        f"Average threat response time: {avg_response}",
        f"Network uptime percentage: {round(network_uptime, 2)}",
        "",
        "Top threats:",
    ]
    lines.extend(f"- {e.id} {e.name}: {e.priority_score_global}" for e in sim.manager.priority_table[:5])
    lines.extend(["", "Final entity states:"])
    lines.extend(f"- {e.id} {e.name} {e.allegiance} {e.entity_type} active={e.active} status={e.status_text}" for e in sim.all_entities)
    lines.extend(["", "Event log:"])
    lines.extend(f"[{e.step}] {e.event_type}: {e.message}" for e in sim.state.events)
    lines.extend(["", "Effects are abstract simulation-only representations."])
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    return {"txt": txt_path, "entities": entity_path, "events": event_path, "summary": summary_path}


def _write_csv(path: Path, rows: list[dict]) -> None:
    """Write CSV using stdlib only.

    Lists/dicts are encoded as compact JSON strings so position, velocity, path,
    and similar structured fields remain readable without requiring pandas.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _csv_value(value) -> str | int | float | bool | None:
    if isinstance(value, (list, dict)):
        return json.dumps(value, separators=(",", ":"))
    return value
