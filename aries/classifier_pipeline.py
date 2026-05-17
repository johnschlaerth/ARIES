"""Batch image classification pipeline for ARIES."""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from .classifier import ImageClassifier
from .config_loader import resolve_project_path
from .models import ClassificationResult
from .utils import write_json

CLASSIFIED_ENTITIES_PATH = "config/classified_entities.json"


def pick_classifiable_images(config: dict[str, Any], count: int | None = None) -> list[Path]:
    """Pick a random sample of jpg/jpeg/png files from the image folder.

    Filters out avif/webp/jxl/etc. that PIL cannot reliably open.
    """
    image_folder = resolve_project_path(config, config["paths"]["image_folder"])
    supported = sorted(
        p for p in image_folder.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not supported:
        return []
    n = count if count is not None else random.randint(4, min(10, len(supported)))
    n = min(n, len(supported))
    return random.sample(supported, n)


def run_classification_batch(
    config: dict[str, Any],
    count: int | None = None,
    mode: str = "api",
) -> Generator[tuple[int, int, Path, ClassificationResult], None, None]:
    """Classify a random batch of images, yielding progress after each one.

    Yields:
        (index_1based, total, image_path, result)

    Writes config/classified_entities.json when all images are done.
    """
    images = pick_classifiable_images(config, count)
    total = len(images)
    classifier = ImageClassifier(config)
    results: list[dict[str, Any]] = []

    for i, image_path in enumerate(images, start=1):
        result = classifier.classify(image_path, mode=mode)
        results.append({
            "entity_id": f"CLS_{i}",
            "image_path": str(image_path.relative_to(Path(config["_root"]))),
            "classification": result.to_dict(),
        })
        yield i, total, image_path, result

    _write_classified_entities(config, results)


def _write_classified_entities(config: dict[str, Any], results: list[dict[str, Any]]) -> None:
    root = Path(config["_root"])
    output_path = root / CLASSIFIED_ENTITIES_PATH
    write_json(output_path, {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "image_count": len(results),
        "entities": results,
    })


def load_classified_entities(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Load classified entities from the persistent JSON, or return []."""
    path = Path(config["_root"]) / CLASSIFIED_ENTITIES_PATH
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f).get("entities", [])
    except Exception:
        return []
