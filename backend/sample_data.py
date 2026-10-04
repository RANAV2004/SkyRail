import csv
import os
from typing import Dict, Tuple

_EDGES = [
    # North / west
    ("Delhi", "Jaipur", 280),
    ("Delhi", "Lucknow", 555),
    ("Delhi", "Ahmedabad", 940),
    ("Delhi", "Bhopal", 705),
    ("Jaipur", "Ahmedabad", 675),
    ("Jaipur", "Mumbai", 1150),
    ("Ahmedabad", "Mumbai", 525),
    ("Mumbai", "Pune", 150),
    ("Mumbai", "Nagpur", 835),
    ("Bhopal", "Mumbai", 840),
    ("Bhopal", "Nagpur", 390),
    # North / east
    ("Lucknow", "Varanasi", 300),
    ("Lucknow", "Kolkata", 985),
    ("Lucknow", "Patna", 530),
    ("Varanasi", "Patna", 230),
    ("Patna", "Kolkata", 585),
    # Central
    ("Nagpur", "Hyderabad", 575),
    ("Nagpur", "Raipur", 290),
    ("Raipur", "Kolkata", 890),
    ("Raipur", "Bhubaneswar", 560),
    # South
    ("Mumbai", "Hyderabad", 710),
    ("Pune", "Hyderabad", 560),
    ("Hyderabad", "Bangalore", 570),
    ("Hyderabad", "Chennai", 625),
    ("Bangalore", "Chennai", 350),
    ("Bangalore", "Pune", 840),
    # East coast
    ("Hyderabad", "Visakhapatnam", 710),
    ("Chennai", "Visakhapatnam", 780),
    ("Visakhapatnam", "Bhubaneswar", 440),
    ("Bhubaneswar", "Kolkata", 440),
]

CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "Delhi": (28.6139, 77.2090),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
    "Ahmedabad": (23.0225, 72.5714),
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Bhopal": (23.2599, 77.4126),
    "Nagpur": (21.1458, 79.0882),
    "Varanasi": (25.3176, 82.9739),
    "Patna": (25.5941, 85.1376),
    "Kolkata": (22.5726, 88.3639),
    "Raipur": (21.2514, 81.6296),
    "Bhubaneswar": (20.2961, 85.8245),
    "Visakhapatnam": (17.6868, 83.2185),
    "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707),
    "Bangalore": (12.9716, 77.5946),
}


_AVG_SPEED_KMPH = 65.0


def sample_train_graph() -> Dict[str, Dict[str, float]]:
    """Return the undirected weighted city graph as an adjacency dict."""
    graph: Dict[str, Dict[str, float]] = {}
    for a, b, dist in _EDGES:
        graph.setdefault(a, {})[b] = float(dist)
        graph.setdefault(b, {})[a] = float(dist)
    return graph


def network():
    """Cities with coordinates plus the undirected edge list (for the map)."""
    return {
        "cities": [
            {"name": c, "lat": CITY_COORDS[c][0], "lon": CITY_COORDS[c][1]}
            for c in sorted(CITY_COORDS)
        ],
        "edges": [{"a": a, "b": b, "distance": d} for a, b, d in _EDGES],
    }


def city_list():
    """Sorted list of all cities in the network."""
    return sorted(sample_train_graph().keys())


def estimated_time(distance_km: float) -> float:
    """Rough travel time in hours for a given distance."""
    return round(distance_km / _AVG_SPEED_KMPH, 2)

# Train no. Tracks
SAMPLE_TRAINS = [
    (12951, "Mumbai Rajdhani", ["Delhi", "Jaipur", "Mumbai"], "16:25", 82),
    (12015, "Ajmer Shatabdi", ["Delhi", "Jaipur"], "06:05", 72),
    (12958, "Swarna Jayanti Rajdhani", ["Delhi", "Jaipur", "Ahmedabad"], "19:55", 74),
    (
        12907,
        "Maharashtra Sampark Kranti",
        ["Mumbai", "Ahmedabad", "Delhi"],
        "17:15",
        70,
    ),
    (12009, "Ahmedabad Shatabdi", ["Mumbai", "Ahmedabad"], "06:20", 76),
    (12123, "Deccan Queen", ["Mumbai", "Pune"], "17:10", 55),
    (
        12303,
        "Poorva Express",
        ["Delhi", "Lucknow", "Varanasi", "Patna", "Kolkata"],
        "17:00",
        64,
    ),
    (12301, "Howrah Rajdhani", ["Delhi", "Lucknow", "Kolkata"], "16:50", 80),
    (12309, "Patna Rajdhani", ["Delhi", "Lucknow", "Patna"], "17:10", 76),
    (12430, "Lucknow AC Express", ["Delhi", "Lucknow"], "20:50", 70),
    (
        12333,
        "Vibhuti Express",
        ["Lucknow", "Varanasi", "Patna", "Kolkata"],
        "20:00",
        58,
    ),
    (
        12801,
        "Purushottam Express",
        ["Bhubaneswar", "Kolkata", "Patna", "Varanasi", "Lucknow", "Delhi"],
        "21:35",
        66,
    ),
    (
        12621,
        "Tamil Nadu Express",
        ["Delhi", "Bhopal", "Nagpur", "Hyderabad", "Chennai"],
        "22:30",
        72,
    ),
    (
        12723,
        "Telangana Express",
        ["Hyderabad", "Nagpur", "Bhopal", "Delhi"],
        "06:30",
        68,
    ),
    (
        12627,
        "Karnataka Express",
        ["Bangalore", "Hyderabad", "Nagpur", "Bhopal", "Delhi"],
        "19:20",
        64,
    ),
    (12155, "Bhopal Express", ["Bhopal", "Delhi"], "20:40", 66),
    (
        18237,
        "Chhattisgarh Express",
        ["Raipur", "Nagpur", "Bhopal", "Delhi"],
        "14:15",
        55,
    ),
    (12701, "Hussainsagar Express", ["Mumbai", "Pune", "Hyderabad"], "21:45", 56),
    (12163, "Chennai Express", ["Mumbai", "Pune", "Hyderabad", "Chennai"], "20:35", 58),
    (12608, "Lalbagh Express", ["Bangalore", "Chennai"], "06:20", 62),
    (12728, "Godavari Express", ["Hyderabad", "Visakhapatnam"], "17:40", 58),
    (
        12703,
        "Falaknuma Express",
        ["Hyderabad", "Visakhapatnam", "Bhubaneswar", "Kolkata"],
        "07:45",
        66,
    ),
    (
        18045,
        "East Coast Express",
        ["Hyderabad", "Visakhapatnam", "Bhubaneswar", "Kolkata"],
        "11:00",
        55,
    ),
    (
        12704,
        "Falaknuma Express",
        ["Kolkata", "Bhubaneswar", "Visakhapatnam", "Hyderabad"],
        "08:15",
        66,
    ),
    (
        12129,
        "Azad Hind Express",
        ["Pune", "Hyderabad", "Nagpur", "Raipur", "Kolkata"],
        "18:35",
        60,
    ),
    (
        12839,
        "Howrah Mail",
        ["Chennai", "Visakhapatnam", "Bhubaneswar", "Kolkata"],
        "23:45",
        62,
    ),
    (
        12841,
        "Coromandel Express",
        ["Kolkata", "Bhubaneswar", "Visakhapatnam", "Chennai"],
        "15:20",
        68,
    ),
    (12809, "Howrah Mail", ["Mumbai", "Nagpur", "Raipur", "Kolkata"], "21:10", 62),
    (12810, "Howrah Mail", ["Kolkata", "Raipur", "Nagpur", "Mumbai"], "20:00", 62),
    (
        12859,
        "Gitanjali Express",
        ["Mumbai", "Nagpur", "Raipur", "Kolkata"],
        "06:00",
        68,
    ),
    (
        12833,
        "Howrah Express",
        ["Ahmedabad", "Mumbai", "Nagpur", "Raipur", "Kolkata"],
        "00:25",
        58,
    ),
]

HALT_MINUTES = 10
PREMIUM = ("Rajdhani", "Shatabdi", "AC Express")


def train_timing(stops, departure: str, speed: float):
    """Total km, running minutes and arrival clock time for a train."""
    graph = sample_train_graph()
    km = 0.0
    for a, b in zip(stops, stops[1:]):
        if b not in graph.get(a, {}):
            raise ValueError(f"No track between {a} and {b}")
        km += graph[a][b]
    minutes = round(km / speed * 60 + HALT_MINUTES * max(0, len(stops) - 2))
    h, m = map(int, departure.split(":"))
    end = (h * 60 + m + minutes) % (24 * 60)
    return km, minutes, f"{end // 60:02d}:{end % 60:02d}"


def seed_database(db, models):
    from .network import get_network

    net = get_network()
    existing = {t.train_number: t for t in db.query(models.Train).all()}
    for t in net.trains.values():
        premium = any(p in t["name"] for p in PREMIUM)
        fields = dict(
            train_name=t["name"],
            source=t["source"],
            destination=t["destination"],
            departure=t["departure"],
            arrival=t["arrival"],
            stops=",".join(s["code"] for s in t["stops"]),
            duration_minutes=t["duration_min"],
            fare=float(round(t["distance_km"] * (1.4 if premium else 0.7) / 5) * 5),
        )
        row = existing.get(t["number"])
        if row:
            for k, v in fields.items():
                setattr(row, k, v)
        else:
            db.add(
                models.Train(
                    train_number=t["number"],
                    total_seats=150,
                    available_seats=150,
                    **fields,
                )
            )

    if db.query(models.Route).count() == 0:
        for a, b, dist in _EDGES:
            for s, d in ((a, b), (b, a)):
                db.add(
                    models.Route(
                        source=s,
                        destination=d,
                        distance=float(dist),
                        estimated_time=estimated_time(dist),
                    )
                )
    db.commit()


def export_routes_csv(path: str = "routes.csv"):
    """Write the route table to a CSV file (parity with the report's CSV story)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "destination", "distance_km", "estimated_time_h"])
        for a, b, dist in _EDGES:
            writer.writerow([a, b, dist, estimated_time(dist)])
    return os.path.abspath(path)
