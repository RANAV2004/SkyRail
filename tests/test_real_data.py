

from datetime import datetime, timedelta

import pytest

from backend import route_planner as rp
from backend import weather
from tests.conftest import HAS_MODEL


def test_network_loaded(real_network):
    assert real_network.real
    assert len(real_network.stations) > 4000 and len(real_network.trains) > 3000


def test_every_train_has_a_sane_timetable(real_network):
    for t in real_network.trains.values():
        stops = t["stops"]
        assert stops[-1]["arr"] > stops[0]["dep"], t["name"]
        kmh = t["distance_km"] / (t["duration_min"] / 60)
        assert kmh < 140, f"{t['name']} at {kmh:.0f} km/h"


def test_alternative_routes_are_really_different(real_network):
    alts = rp.alternative_routes(real_network, "SC", "HWH", 4)
    assert len(alts) >= 3
    for i, p in enumerate(alts):
        for q in alts[:i]:
            assert rp._similarity(real_network, p, q) <= 0.6


def test_yen_gives_near_duplicates_on_the_real_network(real_network):
    
    g = real_network.graph
    paths = rp.k_shortest_paths(g, "SC", "HWH", 4)
    first = set(zip(paths[0], paths[0][1:]))
    second = set(zip(paths[1], paths[1][1:]))
    assert len(first & second) / len(first) > 0.9


def test_city_search_finds_trains(real_network):
    day = (datetime.now(weather.IST) + timedelta(days=2)).date()
    res = rp.search_trains(
        real_network.resolve("city:Hyderabad"),
        real_network.resolve("city:Kolkata"),
        day,
    )
    assert res
    for r in res:
        assert r["board"] in real_network.resolve("city:Hyderabad")
        assert r["alight"] in real_network.resolve("city:Kolkata")


@pytest.mark.skipif(not HAS_MODEL, reason="run scripts/train_delay_model.py first")
def test_model_predictions_look_sane(real_network, monkeypatch):
    from backend import delay_model

    monkeypatch.setenv("RAILSKY_NO_MODEL", "0")
    monkeypatch.setattr(delay_model, "_loaded", False)
    monkeypatch.setattr(delay_model, "_model", None)
    model = delay_model.get_model()
    assert model is not None
    train = real_network.trains[12704]
    day = (datetime.now(weather.IST) + timedelta(days=2)).date()
    r = rp.train_journey(train, day)
    assert r["delay_source"] == "model"
    for s in r["stops"]:
        assert 0 <= s["predicted_delay"] <= s["predicted_delay_p90"] <= 720
    m = delay_model.metrics()["metrics"]
    assert m["model_p50"] < m["baseline_history"] < m["baseline_zero"]
