import time

from aries.pathfinding import astar_path, direct_path, high_cost_test_terrain


def test_path_starts_and_ends_near_points():
    terrain = high_cost_test_terrain()
    path = astar_path([5, 5], [95, 95], terrain)
    assert path[0] == [5, 5]
    assert path[-1] == [95, 95]


def test_ground_path_uses_gap_in_high_cost_region():
    terrain = high_cost_test_terrain()
    path = astar_path([5, 50], [95, 50], terrain)
    assert any(40 <= p[0] <= 60 and 40 <= p[1] <= 60 for p in path)


def test_air_direct_path_ignores_terrain():
    assert direct_path([0, 0], [10, 20]) == [[0, 0], [10, 20]]


def test_pathfinding_completes_under_time_limit():
    terrain = high_cost_test_terrain()
    start = time.perf_counter()
    astar_path([0, 0], [99, 99], terrain)
    assert time.perf_counter() - start < 0.5

