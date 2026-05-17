from aries.config_loader import load_config, load_scenario
from aries.simulation import Simulation


def make_sim():
    config = load_config()
    scenario = load_scenario("scenarios/simple_test_scenario.json", config)
    config["simulation"]["start_paused"] = False
    return Simulation(scenario, config)


def test_timestep_advances():
    sim = make_sim()
    sim.step()
    assert sim.state.step == 1


def test_entities_move():
    sim = make_sim()
    start = list(sim.friendlies[0].position)
    sim.step()
    assert sim.friendlies[0].position != start or sim.enemies[0].disabled


def test_dead_entities_do_not_move():
    sim = make_sim()
    enemy = sim.enemies[0]
    enemy.disabled = True
    enemy.alive = False
    start = list(enemy.position)
    sim.step()
    assert enemy.position == start


def test_event_log_updates():
    sim = make_sim()
    sim.step()
    assert sim.state.events


def test_mission_ends_when_all_enemies_disabled():
    sim = make_sim()
    for enemy in sim.enemies:
        enemy.disabled = True
        enemy.alive = False
    sim.step()
    assert sim.state.mission_done
    assert sim.state.outcome == "ALL_THREATS_DISABLED"

