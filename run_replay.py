"""Inspect a saved ARIES replay JSON without Pygame."""

from __future__ import annotations

import argparse
from pathlib import Path

from aries.replay import load_replay


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect an ARIES replay JSON.")
    parser.add_argument("replay_file", help="Path to a replay JSON file.")
    args = parser.parse_args()
    replay = load_replay(Path(args.replay_file))
    frames = replay.get("frames", [])
    print(f"Replay: {replay.get('scenario_name', 'unknown')}")
    print(f"Frames: {len(frames)}")
    if frames:
        first = frames[0]
        last = frames[-1]
        print(f"First step: {first.get('step')}")
        print(f"Last step: {last.get('step')} outcome={last.get('outcome')}")
        print(f"Entities in last frame: {len(last.get('entities', []))}")


if __name__ == "__main__":
    main()
