"""Mock, cached, and optional OpenAI image classification."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config_loader import load_config, resolve_project_path
from .image_utils import compress_image
from .models import ClassificationResult
from .utils import file_sha256, load_json, write_json


class ImageClassifier:
    """Classifier facade with deterministic mock mode as the default."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.root = Path(config["_root"])
        self.mock_table = load_json(self.root / "data" / "mock_classifications.json")
        self.cache_path = resolve_project_path(config, config["paths"]["classification_cache"])
        if self.cache_path.exists():
            self.cache = load_json(self.cache_path)
        else:
            self.cache = {}

    def classify(self, image_path: str | Path, mode: str | None = None) -> ClassificationResult:
        image_path = Path(image_path)
        mode = mode or self.config.get("run_mode", "mock")
        if not image_path.exists():
            return ClassificationResult.safe_unknown(str(image_path), source="missing_file")
        image_hash = file_sha256(image_path)
        # Mock mode is deliberately table-driven so demos/tests can exercise
        # named safety cases even when placeholder image bytes are identical.
        # Cache reuse is primarily to prevent repeated API calls — but only
        # reuse entries that came from a real API call, not stale mock results.
        _stale_sources = {"mock", "fallback", "missing_file", "invalid", "invalid_api_json"}
        if mode != "mock" and self.config.get("openai", {}).get("cache_results", True) and image_hash in self.cache:
            cached = self.cache[image_hash].get("result", {})
            if cached.get("source") not in _stale_sources:
                return ClassificationResult.from_payload(str(image_path), cached, source="cache")
        if mode == "api" and self.config.get("openai", {}).get("enabled", False):
            result = self._classify_api_with_fallback(image_path)
        else:
            result = self._classify_mock(image_path)
        self._save_cache(image_hash, image_path, result)
        return result

    def _classify_mock(self, image_path: Path) -> ClassificationResult:
        key = image_path.name.lower()
        payload = self.mock_table.get(key)
        if payload is None:
            stem = image_path.stem.lower()
            payload = next((value for name, value in self.mock_table.items() if stem in name.lower()), None)
        if payload is None:
            payload = self.mock_table.get("default_unknown", {})
        return ClassificationResult.from_payload(str(image_path), payload, source="mock")

    def _classify_api_with_fallback(self, image_path: Path) -> ClassificationResult:
        compressed: Path | None = None
        try:
            from openai import OpenAI

            openai_cfg = self.config["openai"]
            api_key = os.getenv(openai_cfg.get("api_key_env_var", "OPENAI_API_KEY"))
            if not api_key:
                return self._classify_mock(image_path)
            compressed = compress_image(image_path, self.root / "outputs" / "temp", int(openai_cfg.get("image_max_side_px", 512)))
            encoded = base64.b64encode(compressed.read_bytes()).decode("ascii")
            prompt = (
                "You are a military threat classification AI. Analyze this image and return ONLY a raw JSON object — "
                "no markdown fences, no explanation, just the JSON. Use this exact schema:\n"
                '{"name":"<specific object name, e.g. FPV Drone, T-72 Tank, US Soldier>","allegiance":"<friendly|enemy|neutral|unknown>","domain":"<ground|air|fixed|non_threat>","entity_type":"<enemy_drone|enemy_ground_vehicle|enemy_ew|enemy_infantry|enemy_unknown|friendly_human|friendly_vehicle|neutral_civilian|non_threat_animal|non_threat_object|unknown_contact>","threat_level":<integer 1-10>,"confidence":<float 0.0-1.0>,"description":"<one sentence describing exactly what you see>","rationale":"<one sentence on threat assessment>","should_spawn_in_simulation":<true|false>}\n'
                "Allegiance rules — be decisive, not conservative:\n"
                "- US/NATO military equipment or soldiers = friendly\n"
                "- Russian, Chinese, Iranian, North Korean, or non-NATO adversary military = enemy\n"
                "- FPV drones, loitering munitions, armed UAVs = enemy_drone, allegiance=enemy, threat_level 7-9\n"
                "- Recon drones (Predator/Reaper/military UAV) = enemy_drone if adversary, friendly_vehicle if US/NATO\n"
                "- Armored vehicles with Russian/Soviet markings or Z/V symbols = enemy, threat_level 7-9\n"
                "- Armed infantry in adversary uniforms = enemy_infantry, threat_level 6-8\n"
                "- threat_level scale: 1=civilian/no threat, 3=low risk, 5=armed military, 7=active threat, 9-10=immediate deadly threat\n"
                "- confidence: how certain you are of this classification (0.0=guessing, 0.5=likely, 0.9=certain)\n"
                "- should_spawn_in_simulation: true for any military entity, false for monuments, pets, civilians\n"
                "- If image has no military content, use domain=non_threat, allegiance=neutral, threat_level=1"
            )
            client = OpenAI(api_key=api_key, timeout=openai_cfg.get("timeout_seconds", 20))
            attempts = max(1, int(openai_cfg.get("max_retries", 2)))
            last_result = ClassificationResult.safe_unknown(str(image_path), source="invalid_api_json")
            for _ in range(attempts):
                response = client.chat.completions.create(
                    model=openai_cfg.get("model", "gpt-4o-mini"),
                    messages=[
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                        ]}
                    ],
                )
                text = _extract_json_object(response.choices[0].message.content or "{}")
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    continue
                result = ClassificationResult.from_payload(str(image_path), payload, source="openai")
                if result.source != "invalid":
                    return result
                last_result = result
            return last_result
        except Exception as exc:
            print(f"[classifier] API error for {image_path.name}: {exc}")
            return self._classify_mock(image_path)
        finally:
            if compressed is not None:
                try:
                    compressed.unlink()
                except OSError:
                    pass

    def _save_cache(self, image_hash: str, image_path: Path, result: ClassificationResult) -> None:
        self.cache[image_hash] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": self.config.get("openai", {}).get("model", "mock"),
            "original_image_path": str(image_path),
            "result": result.to_dict(),
        }
        write_json(self.cache_path, self.cache)


def _extract_json_object(text: str) -> str:
    """Tolerate fenced JSON responses while still requiring a JSON object."""

    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return stripped
    return stripped[start : end + 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["mock", "api"], default=None)
    parser.add_argument("--image", default=None)
    parser.add_argument("--folder", default=None)
    parser.add_argument("--enable-api", action="store_true", help="Temporarily enable API mode for this run.")
    args = parser.parse_args()
    config = load_config()
    if args.enable_api:
        config["openai"]["enabled"] = True
        config["run_mode"] = "api"
    classifier = ImageClassifier(config)
    paths: list[Path] = []
    if args.image:
        paths.append(Path(args.image))
    else:
        folder = Path(args.folder) if args.folder else resolve_project_path(config, config["paths"]["image_folder"])
        paths.extend(sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}))
    if not paths:
        print("No images found.")
        return
    for path in paths:
        result = classifier.classify(path, args.mode)
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
