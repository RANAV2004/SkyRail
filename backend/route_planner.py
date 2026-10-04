# route planner (admin side) + train search (passenger side)

import heapq
import math
from datetime import datetime, timedelta

from . import weather
from .delay_model import get_model
from .network import get_network

AVG_SPEED_KMPH = 55.0  #average
DWELL_MINUTES = 5  
MAX_STOP_DELAY = 180  
MAX_PLAUSIBLE_KMPH = 130.0
MAX_KEY_STOPS = 10

NO_RISK = {"delay_minutes": 0, "severity": "unknown", "factors": []}


#graph

def _dijkstra(graph, src, dst, banned_nodes=(), banned_edges=(), weight=None):
    # weight: optional {(a, b): multiplier}, used by the penalty method below
    pq = [(0.0, src, [src])]
    seen = set()
    while pq:
        cost, node, path = heapq.heappop(pq)
        if node in seen:
            continue
        seen.add(node)
        if node == dst:
            return cost, path
        for nxt, km in graph.get(node, {}).items():
            if nxt in seen or nxt in banned_nodes or (node, nxt) in banned_edges:
                continue
            w = km * weight.get((node, nxt), 1.0) if weight else km
            heapq.heappush(pq, (cost + w, nxt, path + [nxt]))
    return math.inf, []


def path_cost(graph, path):
    total = 0
    for a, b in zip(path, path[1:]):
        total += graph[a][b]
    return total


def k_shortest_paths(graph, src, dst, k):
    
    if src not in graph or dst not in graph or src == dst:
        return []
    _, first = _dijkstra(graph, src, dst)
    if not first:
        return []

    found = [first]
    candidates = []  # heap of (distance, path)
    already_queued = set()

    for _ in range(1, k):
        prev = found[-1]
        for i in range(len(prev) - 1):
            spur = prev[i]
            root = prev[: i + 1]
            blocked_edges = set()
            for p in found:
                if p[: i + 1] == root and len(p) > i + 1:
                    blocked_edges.add((p[i], p[i + 1]))
                    blocked_edges.add((p[i + 1], p[i]))
            _, spur_path = _dijkstra(graph, spur, dst, set(root[:-1]), blocked_edges)
            if not spur_path:
                continue
            new_path = root[:-1] + spur_path
            if tuple(new_path) in already_queued or new_path in found:
                continue
            already_queued.add(tuple(new_path))
            heapq.heappush(candidates, (path_cost(graph, new_path), new_path))
        if not candidates:
            break
        found.append(heapq.heappop(candidates)[1])
    return found


def _corridor(net, path, radius):
    out = set()
    for c in path:
        out.update(net.near(c, radius))
    return out


def _similarity(net, p, q):
    # share of p's stations that are within 30 km of route q
    around_q = _corridor(net, q, 30)
    return sum(1 for c in p if c in around_q) / len(p)


def alternative_routes(
    net, src, dst, k=4, penalty=3.0, max_similarity=0.6, max_detour=1.5, tries=10
):
  
    graph = net.graph
    if src not in graph or dst not in graph or src == dst:
        return []
    weight = {}
    found = []
    shortest_km = None
    for _ in range(tries):
        _, p = _dijkstra(graph, src, dst, weight=weight)
        if not p:
            break
        km = path_cost(graph, p)
        if shortest_km is None:
            shortest_km = km
        different = all(
            _similarity(net, p, q) <= max_similarity
            and _similarity(net, q, p) <= max_similarity
            for q in found
        )
        if km <= shortest_km * max_detour and different:
            found.append(p)
            if len(found) == k:
                break
        zone = _corridor(net, p, 25)
        for a in zone:
            for b in graph[a]:
                if b in zone:
                    weight[(a, b)] = weight.get((a, b), 1.0) * penalty
    found.sort(key=lambda p: path_cost(graph, p))
    return found


def key_stops(items, traffic, max_stops=MAX_KEY_STOPS):
    
    if len(items) <= max_stops:
        return list(range(len(items)))
    start, total = items[0][1], items[-1][1] - items[0][1]
    spacing = max(120, total / (max_stops - 1))
    windows = max(0, min(max_stops - 2, round(total / spacing) - 1))
    picked = {0, len(items) - 1}
    for k in range(1, windows + 1):
        lo, hi = start + (k - 0.5) * spacing, start + (k + 0.5) * spacing
        inside = [i for i in range(1, len(items) - 1) if lo <= items[i][1] < hi]
        if inside:
            picked.add(max(inside, key=lambda i: traffic(items[i][0])))
    return sorted(picked)

#weather delay 


def assess_slot(slot):
    if not slot:
        return dict(NO_RISK)

    factors = []
    cid = slot["condition_id"]  # OpenWeatherMap condition code
    rain = slot["rain_mm"]
    vis = slot["visibility"]
    wind = slot["wind_speed"]
    temp = slot["temp"]

    if 200 <= cid < 300:  
        factors.append({"label": "Thunderstorm", "minutes": 90})

    if rain >= 10 or cid in (502, 503, 504, 522, 531):
        factors.append({"label": f"Heavy rain ({rain:g} mm/3h)", "minutes": 55})
    elif rain >= 2.5 or cid in (501, 521):
        factors.append({"label": f"Moderate rain ({rain:g} mm/3h)", "minutes": 20})
    elif rain > 0 or cid in (300, 301, 500, 520):
        factors.append({"label": "Light rain", "minutes": 6})

    if 600 <= cid < 700 or slot.get("snow_mm", 0) > 0:
        factors.append({"label": "Snow", "minutes": 60})

    if vis < 200:
        factors.append({"label": f"Dense fog (visibility {vis} m)", "minutes": 90})
    elif vis < 1000:
        factors.append({"label": f"Fog (visibility {vis} m)", "minutes": 40})
    elif vis < 3000:
        factors.append(
            {"label": f"Reduced visibility ({vis / 1000:.1f} km)", "minutes": 10}
        )

    if wind >= 20:
        factors.append({"label": f"Gale-force winds ({wind:g} m/s)", "minutes": 120})
    elif wind >= 14:
        factors.append({"label": f"Strong winds ({wind:g} m/s)", "minutes": 45})
    elif wind >= 10:
        factors.append({"label": f"Gusty winds ({wind:g} m/s)", "minutes": 15})

    if temp >= 45:
        factors.append(
            {"label": f"Extreme heat ({temp:g}°C), speed restrictions", "minutes": 20}
        )
    elif temp >= 42:
        factors.append({"label": f"Very hot ({temp:g}°C)", "minutes": 8})

    delay = min(MAX_STOP_DELAY, sum(f["minutes"] for f in factors))
    return {"delay_minutes": delay, "severity": _severity(delay), "factors": factors}


def _severity(delay):
    if delay < 10:
        return "low"
    if delay < 35:
        return "moderate"
    if delay < 80:
        return "high"
    return "severe"


def risk_score(total_delay):
    
    return int(round(100 * (1 - math.exp(-total_delay / 150))))


def _fmt_minutes(m):
    m = int(round(m))
    h, mins = divmod(m, 60)
    if h == 0:
        return f"{mins} min"
    if mins == 0:
        return f"{h}h"
    return f"{h}h {mins:02d}m"


def _clean(dt):
    return dt.replace(second=0, microsecond=0).isoformat()


# route planner for planner  


def evaluate_route(net, path, departure, forecasts, keys):
    graph = net.graph
    cum = [0.0]
    for a, b in zip(path, path[1:]):
        cum.append(cum[-1] + graph[a][b])

    stops = []
    elapsed = 0.0  # minutes since departure, includes weather delays so far
    base = 0.0  # same thing without weather
    total_delay = 0.0
    beyond_horizon = False
    last_km = 0.0

    for n, i in enumerate(keys):
        code = path[i]
        leg_km = cum[i] - last_km
        last_km = cum[i]
        leg_min = leg_km / AVG_SPEED_KMPH * 60
        elapsed += leg_min
        base += leg_min

        eta = departure + timedelta(minutes=elapsed)
        fc = forecasts[code]
        slot = weather.slot_at(fc, eta)
        horizon = weather.forecast_horizon(fc)
        past_horizon = bool(
            horizon and eta > horizon + timedelta(hours=1.5)
        )  # free OWM = 5 days
        beyond_horizon = beyond_horizon or past_horizon
        risk = assess_slot(slot)

        stops.append(
            {
                "code": code,
                "city": net.name(code),
                "lat": fc["lat"],
                "lon": fc["lon"],
                "eta": _clean(eta),
                "cumulative_km": round(cum[i]),
                "leg_km": round(leg_km),
                "forecast": slot,
                "forecast_beyond_horizon": past_horizon,
                "risk": risk,
            }
        )

       
        total_delay += risk["delay_minutes"]
        elapsed += risk["delay_minutes"]
        if 0 < n < len(keys) - 1:
            elapsed += DWELL_MINUTES
            base += DWELL_MINUTES

    worst = max(stops, key=lambda s: s["risk"]["delay_minutes"])
    
    via = [net.name(path[i]) for i in keys[1:-1]][:4]
    return {
        "path": path,
        "via": via,
        "distance_km": round(cum[-1]),
        "base_minutes": round(base),
        "weather_delay_minutes": round(total_delay),
        "adjusted_minutes": round(base + total_delay),
        "arrival": _clean(departure + timedelta(minutes=base + total_delay)),
        "risk_score": risk_score(total_delay),
        "worst_stop": worst["city"] if worst["risk"]["delay_minutes"] > 0 else None,
        "stops": stops,
        "forecast_beyond_horizon": beyond_horizon,
    }


def _hazards(route, limit=3):
    items = []
    for s in route["stops"]:
        r = s["risk"]
        if r["delay_minutes"] <= 0:
            continue
        when = datetime.fromisoformat(s["eta"]).strftime("%a %H:%M")
        biggest = max(r["factors"], key=lambda f: f["minutes"])["label"]
        name = biggest.split(" (")[0].lower()  # "Heavy rain (14 mm/3h)" -> "heavy rain"
        items.append((r["delay_minutes"], f"{name} near {s['city']} around {when}"))
    items.sort(reverse=True)
    return [text for _, text in items[:limit]]


def _via(route):
    if not route["via"]:
        return "direct"
    return "via " + ", ".join(route["via"])


def _join_names(names):
    if not names:
        return "direct"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def explain(routes, best, shortest):
    reasons = []
    n = len(best["stops"])
    calm = len([s for s in best["stops"] if s["risk"]["delay_minutes"] == 0])
    delay = best["weather_delay_minutes"]

    if best is shortest:
        if delay <= 15:
            if delay:
                extra = f"Expected weather delay is only {_fmt_minutes(delay)}."
            else:
                extra = "No weather delay expected."
            reasons.append(
                f"This is the shortest route ({_via(best)}, {best['distance_km']} km) "
                f"and the weather on it is fine. {extra}"
            )
        else:
            reasons.append(
                f"Still the shortest route ({_via(best)}) even with {_fmt_minutes(delay)} "
                f"of weather delay. The other routes lose more time to extra distance "
                f"or their own weather."
            )
    else:
        extra_km = best["distance_km"] - shortest["distance_km"]
        saved = shortest["adjusted_minutes"] - best["adjusted_minutes"]
        reasons.append(
            f"Going through {_join_names(best['via'])} adds {extra_km} km over the shortest "
            f"route, but it should arrive about {_fmt_minutes(saved)} sooner."
        )
        hz = _hazards(shortest, 2)
        if hz:
            line = (
                f"Route {shortest['label']} ({_via(shortest)}) loses "
                f"{_fmt_minutes(shortest['weather_delay_minutes'])} to weather. "
                f"The worst of it is {hz[0]}."
            )
            if len(hz) > 1:
                line += f" There's also {hz[1]}."
            reasons.append(line)

    if calm == n:
        reasons.append(
            f"No weather hazards at any of the {n} main stops when the train passes."
        )
    else:
        reasons.append(
            f"Weather is calm at {calm} of {n} main stops when the train passes."
        )
        own = _hazards(best, 2)
        if own:
            reasons.append(f"Keep an eye on {' and '.join(own)}.")

    others = [r for r in routes if r is not best and r is not shortest]
    if others:
        runner_up = min(others, key=lambda r: r["adjusted_minutes"])
        diff = runner_up["adjusted_minutes"] - best["adjusted_minutes"]
        reasons.append(
            f"Route {runner_up['label']} ({_via(runner_up)}) is the next best option, "
            f"{_fmt_minutes(diff)} slower."
        )

    if best["forecast_beyond_horizon"]:
        reasons.append(
            "The last few stops are past the 5-day forecast, so they use the "
            "latest forecast available."
        )
    return reasons


def plan(source, destination, departure, k=4):
    net = get_network()
    paths = alternative_routes(net, source, destination, k)
    if not paths:
        return {
            "source": source,
            "destination": destination,
            "routes": [],
            "recommended_index": None,
            "reasons": [],
        }

    traffic = lambda c: net.stations[c]["trains"]
    keys_per_route = []
    for p in paths:
        cum = [0.0]
        for a, b in zip(p, p[1:]):
            cum.append(cum[-1] + net.graph[a][b])
        keys_per_route.append(key_stops(list(zip(p, cum)), traffic))

    wanted = {p[i] for p, keys in zip(paths, keys_per_route) for i in keys}
    forecasts = weather.get_forecasts(wanted)  # each station once, not once per route
    routes = [
        evaluate_route(net, p, departure, forecasts, keys)
        for p, keys in zip(paths, keys_per_route)
    ]

    shortest = routes[0]  # sorted by distance
    best = min(
        routes, key=lambda r: (r["adjusted_minutes"], r["risk_score"], r["distance_km"])
    )

    for i, r in enumerate(routes):
        r["id"] = i
        r["label"] = "ABCDEF"[i]
        r["is_shortest"] = r is shortest
        r["is_recommended"] = r is best

    return {
        "source": source,
        "destination": destination,
        "source_name": net.name(source),
        "destination_name": net.name(destination),
        "departure": departure.isoformat(),
        "weather_source": weather.source_label(forecasts),
        "algorithm": f"penalty method, {len(routes)} different corridors compared",
        "routes": routes,
        "recommended_index": best["id"],
        "shortest_index": shortest["id"],
        "reasons": explain(routes, best, shortest),
        "time_saved_minutes": shortest["adjusted_minutes"] - best["adjusted_minutes"],
        "stations_checked": len(wanted),
    }


# ======================= passenger side =======================


def parse_hhmm(value):
    try:
        h, m = value.strip().split(":")[:2]
        return int(h), int(m)
    except (ValueError, AttributeError):
        return None


def schedule_minutes(departure, arrival, distance_km):
    # only used if a train has no duration stored. if arrival < departure it's the
    # next day, and if the speed still comes out crazy (>130 km/h) it's 2-3 days
    dep = parse_hhmm(departure)
    arr = parse_hhmm(arrival)
    if not dep or not arr:
        return distance_km / AVG_SPEED_KMPH * 60
    minutes = (arr[0] * 60 + arr[1]) - (dep[0] * 60 + dep[1])
    if minutes <= 0:
        minutes += 24 * 60
    while distance_km / (minutes / 60) > MAX_PLAUSIBLE_KMPH:
        minutes += 24 * 60
    return float(minutes)


def _advisory_kind(label):
    low = label.lower()
    if "thunder" in low:
        return "storm"
    if "fog" in low or "visib" in low:
        return "fog"
    if "wind" in low:
        return "wind"
    if "heat" in low or "hot" in low:
        return "heat"
    if "snow" in low:
        return "snow"
    return "rain"


def _passenger_advisories(stops, total_delay):
    notes = []
    risky = [s for s in stops if s["risk"]["factors"]]
    risky.sort(key=lambda s: -s["risk"]["delay_minutes"])

    for s in risky[:3]:
        top = max(s["risk"]["factors"], key=lambda f: f["minutes"])["label"].split(
            " ("
        )[0]
        when = datetime.fromisoformat(s["eta"]).strftime("%I:%M %p").lstrip("0")
        notes.append(
            {
                "level": s["risk"]["severity"],
                "kind": _advisory_kind(top),
                "text": f"{top} near {s['city']} around {when}.",
            }
        )

    with_fc = [s for s in stops if s["forecast"]]
    if not risky and with_fc:
        notes.append(
            {
                "level": "low",
                "kind": "clear",
                "text": "No bad weather forecast along this route.",
            }
        )

    rainy = [
        s["city"]
        for s in with_fc
        if s["forecast"]["rain_mm"] > 0 or s["forecast"]["pop"] >= 0.5
    ]
    if rainy:
        notes.append(
            {
                "level": "info",
                "kind": "umbrella",
                "text": f"Rain likely near {', '.join(rainy[:3])}. Take an umbrella.",
            }
        )

    if with_fc:
        last = with_fc[-1]
        t = last["forecast"]["temp"]
        if t >= 36:
            notes.append(
                {
                    "level": "info",
                    "kind": "water",
                    "text": f"{last['city']} will be around {t:.0f}°C when you arrive. Keep water with you.",
                }
            )
        elif t <= 15:
            notes.append(
                {
                    "level": "info",
                    "kind": "jacket",
                    "text": f"{last['city']} will be around {t:.0f}°C when you arrive. Bring a jacket.",
                }
            )

    if total_delay >= 60:
        notes.append(
            {
                "level": "info",
                "kind": "clock",
                "text": "If you have an onward connection, leave some extra time.",
            }
        )
    return notes


def _model_weather(slot):
   
    if not slot:
        return {"precip": None, "wind": None, "thunder": 0.0, "temp": None}
    return {
        "precip": slot["rain_mm"] / 3,  # mm per 3h -> mm per hour
        "wind": slot["wind_speed"] * 3.6,  # m/s -> km/h
        "thunder": 1.0 if 200 <= slot["condition_id"] < 300 else 0.0,
        "temp": slot["temp"],
    }


def runs_on(train, origin_date):
    days = train.get("run_days", "daily")
    return days == "daily" or str(origin_date.weekday()) in days.split(",")


def train_journey(train, board_date, source=None, destination=None):
  
    net = get_network()
    stops = train["stops"]
    codes = [s["code"] for s in stops]
    src = source or codes[0]
    dst = destination or codes[-1]
    note = None
    if src not in codes or dst not in codes or codes.index(src) >= codes.index(dst):
        note = f"{train['name']} doesn't run {net.name(src)} to {net.name(dst)}, so this is the forecast for its full run."
        src, dst = codes[0], codes[-1]
    i, j = codes.index(src), codes.index(dst)

    # stop times are minutes from midnight of the day the train left its first station
    origin_date = board_date - timedelta(days=stops[i]["dep"] // 1440)
    origin = datetime(
        origin_date.year, origin_date.month, origin_date.day, tzinfo=weather.IST
    )
    departure = origin + timedelta(minutes=stops[i]["dep"])
    arrival_sched = origin + timedelta(minutes=stops[j]["arr"])
    section = stops[i : j + 1]

    picked = key_stops(
        [(s["code"], s["km"]) for s in section], lambda c: net.stations[c]["trains"]
    )
    key = [section[k] for k in picked]
    forecasts = weather.get_forecasts([s["code"] for s in key])
    now = datetime.now(weather.IST)
    horizons = [weather.forecast_horizon(f) for f in forecasts.values()]
    horizon = min(h for h in horizons if h)

    out_stops = []
    rule_delay = 0.0
    model_rows = []
    for s in key:
        eta = origin + timedelta(minutes=s["arr"] if s is not section[0] else s["dep"])
        if now - timedelta(hours=3) <= eta <= horizon + timedelta(hours=1.5):
            slot = weather.slot_at(
                forecasts[s["code"]], eta + timedelta(minutes=rule_delay)
            )
        else:
            slot = None
        risk = assess_slot(slot) if slot else dict(NO_RISK)
        rule_delay += risk["delay_minutes"]
        st = net.stations[s["code"]]
        out_stops.append(
            {
                "code": s["code"],
                "city": st["name"],
                "lat": st["lat"],
                "lon": st["lon"],
                "eta": _clean(eta),
                "cumulative_km": s["km"] - section[0]["km"],
                "forecast": slot,
                "risk": risk,
            }
        )
        model_rows.append(
            {
                "seq": codes.index(s["code"]) + 1,
                "code": s["code"],
                "km": s["km"],
                "hour": (s["arr"] % 1440) // 60,
                "weekday": origin_date.weekday(),
                "traffic": st["trains"],
                "zone": st["zone"],
                **_model_weather(slot),
            }
        )

    covered = len([s for s in out_stops if s["forecast"]])
    model = get_model()
    if model:
        preds = model.predict(train, model_rows)
        for s, (p50, p90) in zip(out_stops, preds):
            s["predicted_delay"] = round(p50)
            s["predicted_delay_p90"] = round(p90)
        # delay at the first stop is "already late when you board", don't count it twice
        delay = max(0.0, preds[-1][0])
        delay_p90 = max(delay, preds[-1][1])
        delay_source = "model"
    else:
        delay = rule_delay
        delay_p90 = rule_delay
        delay_source = "weather rules"

    weather_delay = rule_delay  
    if arrival_sched < now:
        status = "completed"
    elif departure <= now:
        status = "in_progress"
    else:
        status = "upcoming"
    available_from = None
    if covered == 0 and status == "upcoming":
        available_from = (departure - timedelta(days=5)).date().isoformat()
    worst = max(out_stops, key=lambda s: s["risk"]["delay_minutes"])
    section_min = stops[j]["arr"] - stops[i]["dep"]

    return {
        "available": covered > 0,
        "status": status,
        "path": [s["code"] for s in section],
        "path_names": [net.name(s["code"]) for s in section],
        "distance_km": section[-1]["km"] - section[0]["km"],
        "departure": departure.isoformat(),
        "scheduled_arrival": _clean(arrival_sched),
        "expected_arrival": _clean(arrival_sched + timedelta(minutes=delay)),
        "latest_arrival": _clean(arrival_sched + timedelta(minutes=delay_p90)),
        "weather_delay_minutes": round(delay),
        "delay_p90_minutes": round(delay_p90),
        "delay_source": delay_source,
        "weather_only_delay_minutes": round(weather_delay),
        "risk_score": risk_score(weather_delay),
        "severity": worst["risk"]["severity"] if covered else "unknown",
        "stations_with_forecast": covered,
        "forecast_available_from": available_from,
        "advisories": _passenger_advisories(out_stops, delay) if covered else [],
        "stops": out_stops,
        "weather_source": weather.source_label(forecasts),
        "train": {
            "train_number": train["number"],
            "train_name": train["name"],
            "type": train["type"],
            "departure": train["departure"],
            "arrival": train["arrival"],
        },
        "train_path": codes,
        "travel_date": board_date.isoformat(),
        "note": note,
        "scheduled_minutes": section_min,
        "adjusted_minutes": round(section_min + delay),
        "board": src,
        "alight": dst,
        "board_name": net.name(src),
        "alight_name": net.name(dst),
    }


def search_trains(sources, destinations, board_date):
    
    net = get_network()
    options = []
    skipped = 0
    for train, board, alight in net.trains_between(list(sources), list(destinations)):
        stop = next(s for s in train["stops"] if s["code"] == board)
        origin_date = board_date - timedelta(days=stop["dep"] // 1440)
        if not runs_on(train, origin_date):
            skipped += 1
            continue
        options.append(train_journey(train, board_date, board, alight))
    if not options:
        return []
    options.sort(key=lambda o: (o["adjusted_minutes"], o["risk_score"], o["departure"]))

    fastest = min(options, key=lambda o: o["scheduled_minutes"])
    calmest = min(options, key=lambda o: o["weather_only_delay_minutes"])
    rank = 1
    for o in options:
        o["rank"] = rank
        rank += 1
        o["is_fastest_on_paper"] = o is fastest
        o["is_calmest"] = o is calmest and o["available"] and len(options) > 1
        hazards = [
            a
            for a in o["advisories"]
            if a["kind"] not in ("clear", "umbrella", "water", "jacket", "clock")
        ]
        if not o["available"]:
            o["summary"] = (
                "Forecast not out yet. Delay is from this train's usual record."
            )
        elif hazards:
            o["summary"] = hazards[0]["text"]
        else:
            o["summary"] = f"No bad weather at the {len(o['stops'])} main stops."

    best = options[0]
    if best is not fastest:
        gap = best["scheduled_minutes"] - fastest["scheduled_minutes"]
        best["why_first"] = (
            f"{fastest['train']['train_name']} is {_fmt_minutes(gap)} quicker on the "
            f"timetable, but it's expected to run {_fmt_minutes(fastest['weather_delay_minutes'])} "
            f"late, so this one should get you there sooner."
        )
    return options
