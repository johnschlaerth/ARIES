"""ARIES live image classification viewer — step-based with threading.

Press N or SPACE to classify the next image. The API call runs in a background
thread so the UI stays responsive and shows a loading bar while waiting.
When all images are classified, writes config/classified_entities.json.

Usage:
    python run_classifier_gui.py             # API mode, random 4-10 images
    python run_classifier_gui.py --mock      # instant mock mode (no key needed)
    python run_classifier_gui.py --count 6  # classify exactly 6 images
"""

from __future__ import annotations

import argparse
import math
import queue
import sys
import threading
import time
from pathlib import Path

from aries.classifier import ImageClassifier
from aries.classifier_pipeline import (
    CLASSIFIED_ENTITIES_PATH,
    _write_classified_entities,
    pick_classifiable_images,
)
from aries.config_loader import load_config

# ── Layout ────────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1200, 750
IMG_MAX_W, IMG_MAX_H = 620, 640
IMG_X = 14
IMG_Y = 56
PANEL_X = 660
DIVIDER_X = 650

# ── Colors ────────────────────────────────────────────────────────────────────
BG        = (4,  10,  4)
PANEL_BG  = (8,  16,  8)
GREEN     = (0,  220, 80)
DIM_GREEN = (0,  55,  25)
RED       = (240, 40, 40)
YELLOW    = (245, 220, 60)
CYAN      = (0,  220, 230)
WHITE     = (230, 230, 230)
GRAY      = (100, 100, 100)
BLUE      = (60,  120, 255)
ORANGE    = (255, 150, 30)

# ── State machine ─────────────────────────────────────────────────────────────
IDLE      = "idle"       # waiting for first N press
LOADING   = "loading"    # background thread is calling API
RESULT    = "result"     # showing result, waiting for next N
DONE      = "done"       # all images processed


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def pil_to_surface(pygame, path: Path, max_w: int, max_h: int):
    """Convert an image file to a Pygame surface via PIL."""
    from PIL import Image
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((max_w, max_h))
        raw = img.tobytes()
        size = img.size
    return pygame.image.fromstring(raw, size, "RGB")


def allegiance_color(allegiance: str) -> tuple:
    return {
        "enemy":    RED,
        "friendly": GREEN,
        "neutral":  WHITE,
    }.get(allegiance, GRAY)


def threat_bar_color(level: int) -> tuple:
    if level >= 7:
        return RED
    if level >= 4:
        return ORANGE
    return GREEN


# ─────────────────────────────────────────────────────────────────────────────
# Background classification thread
# ─────────────────────────────────────────────────────────────────────────────

def _classify_worker(
    classifier: ImageClassifier,
    image_path: Path,
    mode: str,
    result_q: queue.Queue,
) -> None:
    try:
        result = classifier.classify(image_path, mode=mode)
        result_q.put(("ok", result))
    except Exception as exc:
        result_q.put(("error", str(exc)))


# ─────────────────────────────────────────────────────────────────────────────
# Drawing helpers
# ─────────────────────────────────────────────────────────────────────────────

def draw_loading_bar(pygame, screen, small, img_path: Path, idx: int, total: int, t: float) -> None:
    """Animated scanning bar shown while the API call is in progress."""
    bar_x = PANEL_X
    bar_y = 100
    bar_w = SCREEN_W - PANEL_X - 20
    bar_h = 22

    screen.blit(small.render(f"Classifying {idx}/{total}: {img_path.name[:36]}", True, YELLOW),
                (bar_x, 62))
    screen.blit(small.render("Waiting for AI response...", True, GRAY), (bar_x, 84))

    # Background track
    pygame.draw.rect(screen, (20, 40, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

    # Bouncing scanner block
    period = 1.8
    phase = (t % period) / period
    # Goes 0→1→0 (ping-pong)
    ping = phase * 2 if phase < 0.5 else 2.0 - phase * 2
    block_w = bar_w // 4
    block_x = bar_x + int(ping * (bar_w - block_w))
    pygame.draw.rect(screen, CYAN, (block_x, bar_y, block_w, bar_h), border_radius=4)
    pygame.draw.rect(screen, DIM_GREEN, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

    # Elapsed time
    elapsed = int(t % 100)
    screen.blit(small.render(f"  {elapsed}s elapsed", True, GRAY), (bar_x, bar_y + bar_h + 6))


def draw_result_panel(pygame, screen, font, small, results: list, current_idx: int, state: str) -> None:
    """Right panel: completed results list."""
    rx = PANEL_X

    # Header
    count_label = f"CLASSIFIED: {current_idx}" if state != DONE else f"ALL {current_idx} CLASSIFIED"
    screen.blit(font.render("CLASSIFICATION RESULTS", True, YELLOW), (rx, 20))
    screen.blit(small.render(count_label, True, CYAN), (rx, 40))
    pygame.draw.line(screen, DIM_GREEN, (rx, 56), (SCREEN_W - 10, 56), 1)

    y = 62
    row_gap = 70
    for entry in results[-(8):]:
        if y + row_gap > SCREEN_H - 60:
            break
        r = entry["result"]
        ac = allegiance_color(r.allegiance)
        eid = entry["entity_id"]

        # Entity name + ID
        screen.blit(small.render(f"{eid}: {r.name[:30]}", True, ac), (rx, y))
        y += 16

        # Type + domain
        screen.blit(small.render(f"  {r.entity_type:<22} {r.domain}", True, WHITE), (rx, y))
        y += 14

        # Confidence bar
        conf_w = int((SCREEN_W - rx - 20) * r.confidence)
        conf_color = GREEN if r.confidence >= 0.65 else YELLOW if r.confidence >= 0.35 else RED
        pygame.draw.rect(screen, (20, 40, 20), (rx, y, SCREEN_W - rx - 20, 8), border_radius=3)
        pygame.draw.rect(screen, conf_color, (rx, y, max(4, conf_w), 8), border_radius=3)
        y += 10

        # Threat level bar
        thr_w = int((SCREEN_W - rx - 20) * (r.threat_level / 10))
        pygame.draw.rect(screen, (40, 20, 20), (rx, y, SCREEN_W - rx - 20, 6), border_radius=3)
        pygame.draw.rect(screen, threat_bar_color(r.threat_level), (rx, y, max(4, thr_w), 6), border_radius=3)
        y += 8

        # Compact stats
        screen.blit(small.render(
            f"  conf {r.confidence:.0%}  threat {r.threat_level}/10  spawn={r.should_spawn_in_simulation}",
            True, GRAY), (rx, y))
        y += 12

        pygame.draw.line(screen, DIM_GREEN, (rx, y + 2), (SCREEN_W - 10, y + 2), 1)
        y += 8


def draw_status_bar(pygame, screen, small, state: str, idx: int, total: int) -> None:
    """Bottom status strip."""
    pygame.draw.rect(screen, (0, 18, 8), (0, SCREEN_H - 40, SCREEN_W, 40))
    if state == IDLE:
        msg = f"  {total} images selected  |  Press N or SPACE to classify first image"
        color = YELLOW
    elif state == LOADING:
        msg = f"  Classifying image {idx}/{total}...  |  Q/ESC to quit early"
        color = CYAN
    elif state == RESULT:
        msg = f"  Image {idx}/{total} done  |  Press N or SPACE for next  |  Q/ESC to quit"
        color = GREEN
    else:
        msg = f"  All {idx} images classified  |  Config saved to {CLASSIFIED_ENTITIES_PATH}  |  ESC to exit"
        color = CYAN
    screen.blit(small.render(msg[:110], True, color), (6, SCREEN_H - 26))


def draw_image_panel(pygame, screen, small, surface, img_path: Path | None, state: str) -> None:
    """Left panel: current image with optional overlay."""
    area_rect = pygame.Rect(IMG_X - 4, IMG_Y - 4, DIVIDER_X - IMG_X, SCREEN_H - IMG_Y - 50)
    pygame.draw.rect(screen, PANEL_BG, area_rect)

    if surface is not None:
        sw, sh = surface.get_size()
        cx = IMG_X + (DIVIDER_X - IMG_X - sw) // 2
        cy = IMG_Y + max(0, (area_rect.height - sh) // 2)
        screen.blit(surface, (cx, cy))

        if img_path:
            screen.blit(small.render(img_path.name[:60], True, GRAY), (IMG_X + 4, SCREEN_H - 54))

    if state == LOADING:
        # Semi-transparent dark overlay with scanning line
        overlay = pygame.Surface((DIVIDER_X - IMG_X, area_rect.height))
        overlay.set_alpha(160)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (IMG_X - 4, IMG_Y - 4))
        label = small.render("ANALYZING...", True, CYAN)
        lx = IMG_X + (DIVIDER_X - IMG_X - label.get_width()) // 2
        ly = IMG_Y + area_rect.height // 2 - 10
        screen.blit(label, (lx, ly))

    if state == IDLE and surface is None:
        label = small.render("Press N to load first image", True, DIM_GREEN)
        lx = IMG_X + (DIVIDER_X - IMG_X - label.get_width()) // 2
        ly = IMG_Y + area_rect.height // 2
        screen.blit(label, (lx, ly))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="ARIES live image classifier.")
    parser.add_argument("--count", type=int, default=None,
                        help="Images to classify (default: random 4-10)")
    parser.add_argument("--mock", action="store_true",
                        help="Mock mode — instant, no API key needed")
    args = parser.parse_args()

    try:
        import pygame
    except ImportError:
        sys.exit("Pygame required: pip install -r requirements.txt")

    config = load_config()
    if not args.mock:
        config["openai"]["enabled"] = True
        config["run_mode"] = "api"
    mode = "mock" if args.mock else "api"

    images = pick_classifiable_images(config, count=args.count)
    if not images:
        sys.exit("No classifiable images found in data/images/")

    classifier = ImageClassifier(config)
    total = len(images)

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("ARIES — Live Image Classifier")
    font  = pygame.font.SysFont("courier", 16)
    small = pygame.font.SysFont("courier", 13)
    clock = pygame.time.Clock()

    # Runtime state
    state         = IDLE
    img_index     = 0         # which image we're about to classify (0-based)
    results: list = []        # completed classification entries
    current_surface           = None
    current_img_path: Path | None = None
    result_queue: queue.Queue = queue.Queue()
    loading_start             = 0.0
    written                   = False

    def start_next_classification() -> None:
        nonlocal state, current_surface, current_img_path, loading_start, img_index
        if img_index >= total:
            return
        img_path = images[img_index]
        current_img_path = img_path
        # Load the image surface immediately (fast, PIL local read)
        try:
            current_surface = pil_to_surface(pygame, img_path, IMG_MAX_W, IMG_MAX_H)
        except Exception:
            current_surface = None
        loading_start = time.monotonic()
        state = LOADING
        t = threading.Thread(
            target=_classify_worker,
            args=(classifier, img_path, mode, result_queue),
            daemon=True,
        )
        t.start()

    running = True
    while running:
        now = time.monotonic()
        t_elapsed = now - loading_start if state == LOADING else 0.0

        # ── Events ───────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in {pygame.K_q, pygame.K_ESCAPE}:
                    running = False
                elif event.key in {pygame.K_n, pygame.K_SPACE}:
                    if state in {IDLE, RESULT} and img_index < total:
                        start_next_classification()

        # ── Poll background thread ────────────────────────────────────────────
        if state == LOADING:
            try:
                tag, payload = result_queue.get_nowait()
                if tag == "ok":
                    entry = {
                        "entity_id": f"CLS_{img_index + 1}",
                        "image_path": str(images[img_index].relative_to(
                            Path(config["_root"]))),
                        "classification": payload.to_dict(),
                        "result": payload,
                    }
                    results.append(entry)
                else:
                    print(f"[classifier] Error: {payload}")
                img_index += 1
                if img_index >= total:
                    state = DONE
                    if not written:
                        # Strip internal 'result' key before saving
                        saveable = [
                            {k: v for k, v in e.items() if k != "result"}
                            for e in results
                        ]
                        _write_classified_entities(config, saveable)
                        written = True
                else:
                    state = RESULT
            except queue.Empty:
                pass  # still waiting

        # ── Draw ─────────────────────────────────────────────────────────────
        screen.fill(BG)

        # Header
        pygame.draw.rect(screen, (0, 25, 12), (0, 0, SCREEN_W, 50))
        screen.blit(font.render("ARIES  LIVE CLASSIFIER", True, GREEN), (12, 14))
        mode_label = f"{'MOCK' if args.mock else 'API'} MODE  |  {total} IMAGES"
        screen.blit(small.render(mode_label, True, CYAN), (SCREEN_W - 220, 18))

        # Divider
        pygame.draw.line(screen, DIM_GREEN, (DIVIDER_X, 50), (DIVIDER_X, SCREEN_H - 40), 1)

        # Left: image panel
        draw_image_panel(pygame, screen, small, current_surface, current_img_path, state)

        # Right: result panel or loading bar
        if state == LOADING:
            draw_loading_bar(pygame, screen, small, current_img_path, img_index + 1, total, t_elapsed)
        draw_result_panel(pygame, screen, font, small, results, img_index, state)

        # Status bar
        draw_status_bar(pygame, screen, small, state, img_index, total)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
