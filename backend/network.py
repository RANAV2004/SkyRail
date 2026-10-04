# rail network, loaded once. uses data/processed/ if build_data.py has been run,
# otherwise falls back to the old 17 city network (tests use that too)

import math
import os
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv("RAILSKY_DATA", os.path.join(ROOT, "data", "processed"))


def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


class Network:
    def __init__(self):
        self.stations = {}  # code -> {code, name, lat, lon, zone, trains}
        self.graph = defaultdict(dict)  # code -> {code: km}
        self.trains = {}  # number -> {number, name, ..., stops: [...]}
        self.real = False
        self._grid = None

    # ---------- loading
    @classmethod
    def load(cls, data_dir=DATA_DIR):
        net = cls()
        if os.getenv("RAILSKY_SAMPLE") != "1" and os.path.exists(
            os.path.join(data_dir, "trains.csv")
        ):
            net._load_real(data_dir)
        else:
            net._load_sample()
        return net

    def _load_real(self, data_dir):
        import pandas as pd
        from .cities import DISPLAY_NAMES

        st = pd.read_csv(os.path.join(data_dir, "stations.csv"))
        for r in st.itertuples(index=False):
            self.stations[r.code] = {
                "code": r.code,
                "name": DISPLAY_NAMES.get(r.code, " ".join(r.name.split())),
                "lat": r.lat,
                "lon": r.lon,
                "zone": r.zone if isinstance(r.zone, str) else "",
                "trains": int(r.trains),
            }
        ed = pd.read_csv(os.path.join(data_dir, "edges.csv"))
        for a, b, km in ed[["a", "b", "km"]].itertuples(index=False):
            self.graph[a][b] = float(km)
            self.graph[b][a] = float(km)

        tr = pd.read_csv(os.path.join(data_dir, "trains.csv"), dtype={"run_days": str})
        for r in tr.itertuples(index=False):
            self.trains[int(r.number)] = {
                "number": int(r.number),
                "name": r.name,
                "type": r.type,
                "source": r.source,
                "destination": r.destination,
                "departure": r.departure,
                "arrival": r.arrival,
                "duration_min": int(r.duration_min),
                "distance_km": int(r.distance_km),
                "run_days": r.run_days if isinstance(r.run_days, str) else "daily",
                "stops": [],
            }
        sp = pd.read_csv(os.path.join(data_dir, "stops.csv"))
        for r in sp.itertuples(index=False):
            t = self.trains.get(int(r.train))
            if t is not None:
                t["stops"].append(
                    {
                        "code": r.code,
                        "km": int(r.km),
                        "arr": int(r.arr),
                        "dep": int(r.dep),
                        "day": int(r.day),
                    }
                )
        self.real = True

    def _load_sample(self):
        # the old 17-city network. station code = city name here
        from .sample_data import CITY_COORDS, SAMPLE_TRAINS, _EDGES, HALT_MINUTES

        for name, (lat, lon) in CITY_COORDS.items():
            self.stations[name] = {
                "code": name,
                "name": name,
                "lat": lat,
                "lon": lon,
                "zone": "",
                "trains": 0,
            }
        for a, b, km in _EDGES:
            self.graph[a][b] = float(km)
            self.graph[b][a] = float(km)
        for number, name, stops, dep, speed in SAMPLE_TRAINS:
            h, m = map(int, dep.split(":"))
            t = h * 60 + m
            km = 0
            rows = []
            for i, code in enumerate(stops):
                if i > 0:
                    leg = self.graph[stops[i - 1]][code]
                    km += leg
                    t += leg / speed * 60
                arr = round(t)
                if 0 < i < len(stops) - 1:
                    t += HALT_MINUTES
                rows.append(
                    {
                        "code": code,
                        "km": int(km),
                        "arr": arr,
                        "dep": round(t),
                        "day": round(t) // 1440,
                    }
                )
                self.stations[code]["trains"] += 1
            first, last = rows[0], rows[-1]
            self.trains[number] = {
                "number": number,
                "name": name,
                "type": "Express",
                "source": stops[0],
                "destination": stops[-1],
                "departure": dep,
                "arrival": f"{last['arr'] % 1440 // 60:02d}:{last['arr'] % 60:02d}",
                "duration_min": last["arr"] - first["dep"],
                "distance_km": int(km),
                "run_days": "daily",
                "stops": rows,
            }

    # ---------- lookups
    def name(self, code):
        s = self.stations.get(code)
        return s["name"] if s else code

    def coords(self, code):
        s = self.stations[code]
        return s["lat"], s["lon"]

    def search(self, q, limit=10):
        # code match first, then names starting with q, then names containing q.
        # busier stations win ties (nobody means Howrah Halt when they type "howrah")
        q = q.strip().lower()
        if not q:
            return []
        scored = []
        for s in self.stations.values():
            code, name = s["code"].lower(), s["name"].lower()
            if code == q:
                rank = 0
            elif name.startswith(q):
                rank = 1
            elif code.startswith(q):
                rank = 2
            elif q in name:
                rank = 3
            else:
                continue
            scored.append((rank, -s["trains"], s["name"], s))
        scored.sort(key=lambda x: x[:3])
        return [x[3] for x in scored[:limit]]

    def resolve(self, value):
        """'SC' -> ['SC'], 'city:Hyderabad' -> ['SC', 'HYB', ...]. Unknown -> []"""
        from .cities import CITIES

        if value.startswith("city:"):
            return [c for c in CITIES.get(value[5:], []) if c in self.stations]
        return [value] if value in self.stations else []

    def label(self, value):
        return value[5:] if value.startswith("city:") else self.name(value)

    def major(self, n=20):
        return sorted(self.stations.values(), key=lambda s: -s["trains"])[:n]

    def near(self, code, radius_km=30):
        # stations within radius_km, using a coarse lat/lon grid so it isn't O(n)
        if self._grid is None:
            self._grid = defaultdict(list)
            for c, s in self.stations.items():
                self._grid[(int(s["lat"] / 0.3), int(s["lon"] / 0.3))].append(c)
        lat, lon = self.coords(code)
        ci, cj = int(lat / 0.3), int(lon / 0.3)
        out = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for c in self._grid[(ci + di, cj + dj)]:
                    s = self.stations[c]
                    if haversine(lat, lon, s["lat"], s["lon"]) <= radius_km:
                        out.append(c)
        return out

    def trains_between(self, sources, destinations):
        # lists are in preference order. for Kolkata a train calling at Santragachi
        # and then Howrah should get you off at Howrah
        out = []
        for t in self.trains.values():
            codes = [s["code"] for s in t["stops"]]
            board = next((c for c in sources if c in codes), None)
            if board is None:
                continue
            after = codes[codes.index(board) + 1 :]
            alight = next((c for c in destinations if c in after), None)
            if alight:
                out.append((t, board, alight))
        return out

    def map_data(self):
        # compact version for the frontend map: stations as a list, edges as index pairs
        codes = sorted(self.stations)
        idx = {c: i for i, c in enumerate(codes)}
        stations = [
            [
                c,
                self.stations[c]["name"],
                round(self.stations[c]["lat"], 3),
                round(self.stations[c]["lon"], 3),
                self.stations[c]["trains"],
            ]
            for c in codes
        ]
        edges = []
        for a, nbrs in self.graph.items():
            for b in nbrs:
                if a < b and a in idx and b in idx:
                    edges.append([idx[a], idx[b]])
        return {"stations": stations, "edges": edges, "real": self.real}


_network = None


def get_network():
    global _network
    if _network is None:
        _network = Network.load()
    return _network


def reset_network():
    # used by tests to switch between sample and real data
    global _network
    _network = None
