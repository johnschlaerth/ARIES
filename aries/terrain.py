"""Synthetic deterministic terrain generation and sampling."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Terrain:
    """Terrain field used for contour display and movement cost."""

    width: int
    height: int
    seed: int
    elevation: np.ndarray
    cost: np.ndarray

    @classmethod
    def generate(cls, width: int, height: int, seed: int = 42, grid_size: int = 90) -> "Terrain":
        rng = np.random.default_rng(seed)
        xs = np.linspace(0, width, grid_size)
        ys = np.linspace(0, height, grid_size)
        xx, yy = np.meshgrid(xs, ys)
        elevation = np.zeros((grid_size, grid_size), dtype=float)

        # A small set of deterministic Gaussian hills creates contour-like map
        # structure without needing any external map data.
        for _ in range(7):
            cx = rng.uniform(width * 0.15, width * 0.85)
            cy = rng.uniform(height * 0.12, height * 0.88)
            amp = rng.uniform(0.4, 1.2)
            sx = rng.uniform(width * 0.08, width * 0.18)
            sy = rng.uniform(height * 0.08, height * 0.18)
            elevation += amp * np.exp(-(((xx - cx) ** 2) / (2 * sx**2) + ((yy - cy) ** 2) / (2 * sy**2)))

        elevation -= elevation.min()
        if elevation.max() > 0:
            elevation /= elevation.max()
        gy, gx = np.gradient(elevation)
        slope = np.hypot(gx, gy)
        cost = 1.0 + elevation * 3.0 + slope * 25.0
        return cls(width=width, height=height, seed=seed, elevation=elevation, cost=cost)

    def grid_index(self, point: list[float] | tuple[float, float]) -> tuple[int, int]:
        cols = self.cost.shape[1]
        rows = self.cost.shape[0]
        x = int(np.clip(point[0] / self.width * (cols - 1), 0, cols - 1))
        y = int(np.clip(point[1] / self.height * (rows - 1), 0, rows - 1))
        return x, y

    def world_point(self, index: tuple[int, int]) -> list[float]:
        x, y = index
        cols = self.cost.shape[1]
        rows = self.cost.shape[0]
        return [x / (cols - 1) * self.width, y / (rows - 1) * self.height]

    def cost_at(self, point: list[float] | tuple[float, float]) -> float:
        x, y = self.grid_index(point)
        return float(self.cost[y, x])

    def contour_points(self, bands: int = 10) -> list[list[list[float]]]:
        """Return approximate contour point clouds for the renderer.

        Pygame draws these as small dim points. It is intentionally simple and
        robust; exact isoline extraction is unnecessary for the demo.
        """

        levels = np.linspace(0.1, 0.95, bands)
        contours: list[list[list[float]]] = []
        for level in levels:
            mask = np.abs(self.elevation - level) < 0.015
            points = []
            ys, xs = np.where(mask)
            for y, x in zip(ys[::2], xs[::2]):
                points.append(self.world_point((int(x), int(y))))
            contours.append(points)
        return contours
