"""Image compression helpers for optional API classification."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def compress_image(image_path: str | Path, output_dir: str | Path, max_side_px: int = 512) -> Path:
    """Convert an image to RGB JPEG with bounded longest side."""

    image_path = Path(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        image.thumbnail((max_side_px, max_side_px))
        output_path = output_dir / f"{image_path.stem}_compressed.jpg"
        image.save(output_path, "JPEG", quality=85, optimize=True)
        return output_path
