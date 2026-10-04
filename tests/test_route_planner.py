

from datetime import datetime, timedelta

from backend import route_planner as rp
from backend import weather
from backend.network import Network, get_network


def _slot(**over):
    base = dict(
        dt=0,
        temp=28,
        feels_like=28,
        humidity=50,
        condition_id=800,
        condition="Clear",
        description="clear sky",
        wind_speed=3,
        visibility=10000,
        rain_mm=0,
        snow_mm=0,
        pop=0,
    )
    base.update(over)
    return base


def tomorrow():
    return (datetime.now(weather.IST) + timedelta(days=1)).date()


# -graph


def test_yen_returns_loop_free_paths_in_distance_order():
    g = get_network().graph
    paths = rp.k_shortest_paths(g, "Hyderabad", "Kolkata", 5)
    assert len(paths) == 5
    costs = [rp.path_cost(g, p) for p in paths]
    assert costs == sorted(costs)
    for p in paths:
        assert p[0] == "Hyderabad" and p[-1] == "Kolkata"
        assert len(p) == len(set(p)), f"loop in {p}"


def test_first_yen_path_matches_dijkstra():
    from backend.dijkstra import dijkstra

    g = get_network().graph
    _, path = dijkstra(g, "Delhi", "Chennai")
    assert rp.k_shortest_paths(g, "Delhi", "Chennai", 3)[0] == path


def test_unknown_or_same_station_gives_no_paths():
    net = get_network()
    assert rp.k_shortest_paths(net.graph, "Delhi", "Atlantis", 3) == []
    assert rp.alternative_routes(net, "Delhi", "Delhi") == []


def test_alternative_routes_start_with_the_shortest():
    net = get_network()
    alts = rp.alternative_routes(net, "Hyderabad", "Kolkata", 4)
    assert (
        alts and alts[0] == rp.k_shortest_paths(net.graph, "Hyderabad", "Kolkata", 1)[0]
    )
    for p in alts:
        assert p[0] == "Hyderabad" and p[-1] == "Kolkata"


def test_key_stops_keeps_both_ends_and_caps_the_count():
    items = [(f"S{i}", i * 40) for i in range(60)]  # 60 stops over 2,360 km
    picked = rp.key_stops(items, lambda c: 1)
    assert picked[0] == 0 and picked[-1] == 59
    assert len(picked) <= rp.MAX_KEY_STOPS
    assert picked == sorted(picked)


# weather


def test_clear_weather_has_no_delay():
    r = rp.assess_slot(_slot())
    assert r["delay_minutes"] == 0 and r["severity"] == "low"


def test_thunderstorm_and_fog_are_penalised():
    storm = rp.assess_slot(_slot(condition_id=211, rain_mm=15, wind_speed=15))
    fog = rp.assess_slot(_slot(condition_id=741, visibility=150))
    assert storm["severity"] == "severe"
    assert fog["delay_minutes"] >= 90


def test_stop_delay_is_capped():
    worst = rp.assess_slot(
        _slot(condition_id=211, rain_mm=40, wind_speed=30, visibility=50, temp=47)
    )
    assert worst["delay_minutes"] == rp.MAX_STOP_DELAY


def test_plan_recommends_lowest_adjusted_time():
    dep = datetime.now(weather.IST) + timedelta(hours=2)
    result = rp.plan("Hyderabad", "Kolkata", dep, k=4)
    routes = result["routes"]
    assert routes and result["reasons"]
    best = routes[result["recommended_index"]]
    assert best["adjusted_minutes"] == min(r["adjusted_minutes"] for r in routes)
    for r in routes:
        assert r["adjusted_minutes"] == r["base_minutes"] + r["weather_delay_minutes"]
        etas = [s["eta"] for s in r["stops"]]
        assert etas == sorted(etas)


def test_schedule_minutes_handles_overnight_and_multi_day_runs():
    assert rp.schedule_minutes("17:10", "20:25", 150) == 195
    assert rp.schedule_minutes("16:25", "08:15", 1400) == 950
    assert rp.schedule_minutes("22:30", "07:15", 2295) == 32.75 * 60


# passenger


def test_trip_far_ahead_has_no_forecast():
    train = get_network().trains[12703]
    r = rp.train_journey(train, tomorrow() + timedelta(days=15))
    assert r["available"] is False and r["forecast_available_from"]
    assert all(s["forecast"] is None for s in r["stops"])


def test_trip_tomorrow_has_forecast_and_ordered_etas():
    r = rp.train_journey(get_network().trains[12703], tomorrow())
    assert r["available"] and r["status"] == "upcoming"
    etas = [s["eta"] for s in r["stops"]]
    assert etas == sorted(etas)
    assert r["delay_source"] == "weather rules"  # no model in tests


def test_boarding_midway_starts_later_and_is_shorter():
    train = get_network().trains[12129]  # Pune - Hyderabad - Nagpur - Raipur - Kolkata
    full = rp.train_journey(train, tomorrow())
    part = rp.train_journey(train, tomorrow(), "Nagpur", "Kolkata")
    assert part["scheduled_minutes"] < full["scheduled_minutes"]
    assert part["path"][0] == "Nagpur"


def test_wrong_direction_falls_back_to_full_run_with_note():
    r = rp.train_journey(get_network().trains[12129], tomorrow(), "Kolkata", "Nagpur")
    assert r["note"] and r["path"][0] == "Pune"


def test_search_only_returns_trains_in_that_direction_sorted():
    res = rp.search_trains(["Nagpur"], ["Kolkata"], tomorrow())
    assert res
    for r in res:
        assert r["path"][0] == "Nagpur" and r["path"][-1] == "Kolkata"
    adjusted = [r["adjusted_minutes"] for r in res]
    assert adjusted == sorted(adjusted)
    assert [r["rank"] for r in res] == list(range(1, len(res) + 1))


def test_city_search_prefers_main_station_order():
    net = Network()
    net.stations = {
        c: {"code": c, "name": c, "lat": 0, "lon": 0, "zone": "", "trains": 1}
        for c in "ABXY"
    }
    net.trains = {1: {"number": 1, "stops": [{"code": c} for c in ["A", "X", "Y"]]}}
    
    ((_, board, alight),) = net.trains_between(["A"], ["Y", "X"])
    assert (board, alight) == ("A", "Y")
