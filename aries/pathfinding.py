"""Terrain-aware pathfinding for ground entities and direct air paths."""

from __future__ import annotations

import heapq
import math
from typing import Iterable

import numpy as np

from .terrain import Terrain
from .utils import distance


def direct_path(start: list[float], goal: list[float]) -> list[list[float]]:
    """Return the straight-line path used by air entities."""

    return [list(start), list(goal)]


def _neighbors(node: tuple[int, int], shape: tuple[int, int]) -> Iterable[tuple[int, int]]:
    x, y = node
    rows, cols = shape
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < cols and 0 <= ny < rows:
            yield nx, ny


def _simplify(points: list[list[float]], stride: int = 4) -> list[list[float]]:
    if len(points) <= 2:
        return points
    simplified = [points[0]]
    simplified.extend(points[i] for i in range(stride, len(points) - 1, stride))
    simplified.append(points[-1])
    return simplified


def astar_path(start: list[float], goal: list[float], terrain: Terrain) -> list[list[float]]:
    """Compute a deterministic A* path across the terrain cost grid."""

    start_idx = terrain.grid_index(start)
    goal_idx = terrain.grid_index(goal)
    costs = terrain.cost
    open_heap: list[tuple[float, tuple[int, int]]] = [(0.0, start_idx)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score = {start_idx: 0.0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal_idx:
            break
        for nxt in _neighbors(current, costs.shape):
            diagonal = math.sqrt(2.0) if nxt[0] != current[0] and nxt[1] != current[1] else 1.0
            # High terrain cost remains passable but expensive, causing paths to
            # bend around hills when a reasonable alternative exists.
            tentative = g_score[current] + float(costs[nxt[1], nxt[0]]) * diagonal
            if tentative < g_score.get(nxt, float("inf")):
                came_from[nxt] = current
                g_score[nxt] = tentative
                heuristic = distance(nxt, goal_idx)
                heapq.heappush(open_heap, (tentative + heuristic, nxt))

    if goal_idx not in came_from and goal_idx != start_idx:
        return direct_path(start, goal)

    node = goal_idx
    indices = [node]
    while node != start_idx:
        node = came_from[node]
        indices.append(node)
    indices.reverse()
    world = [terrain.world_point(idx) for idx in indices]
    world[0] = list(start)
    world[-1] = list(goal)
    return _simplify(world)


def path_cost(path: list[list[float]], terrain: Terrain) -> float:
    if len(path) < 2:
        return 0.0
    total = 0.0
    for a, b in zip(path, path[1:]):
        total += distance(a, b) * terrain.cost_at(b)
    return float(total)


def high_cost_test_terrain(width: int = 100, height: int = 100) -> Terrain:
    elevation = np.zeros((25, 25), dtype=float)
    cost = np.ones((25, 25), dtype=float)
    cost[:, 11:14] = 30.0
    cost[10:15, 11:14] = 1.0
    return Terrain(width=width, height=height, seed=1, elevation=elevation, cost=cost)
