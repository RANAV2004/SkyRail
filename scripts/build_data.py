import argparse
import io
import json
import math
import os
import sys
import urllib.request
import zipfile
from collections import defaultdict

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "processed")

RSTGCN_ZIP = "https://github.com/KoyenaChowdhury/RSTGCN/raw/main/Indian-Railway-Network-and-Delays.zip"
DATAMEET_STATIONS = (
    "https://raw.githubusercontent.com/datameet/railways/master/stations.json"
)

# stations renamed after 2016, datameet 
OLD_CODES = {
    "DDU": "MGS",
    "VGLJ": "JHS",
    "PRYJ": "ALD",
    "PCOI": "COI",
    "RKMP": "HBJ",
    "CSMT": "CSTM",
    "SMVB": "BYPL",
    "KLBG": "GR",
    "AYC": "FD",
    "SHRN": "BIH",
    "BSBS": "MUV",
    "NDPM": "HBD",
    "MMCT": "BCT",
    "SBIB": "SBI",
    "MBDP": "PBH",
    "MCTM": "UHP",
    "PRRB": "ALY",
    "PYGS": "DRGJ",
    "YNRK": "RKSH",
    "DDCC": "DD",
    "NBJU": "BJU",
    "NKMG": "KXJ",
    "DADN": "MHOW",
}

RSTGCN_FILES = [
    "IRN_edges.csv",
    "stations_zones_mapping.json",
    "train_routes_Sep2024.csv",
    "train_routes_delays_Sep2024.csv",
]


def download(raw_dir):
    os.makedirs(raw_dir, exist_ok=True)
    if not all(os.path.exists(os.path.join(raw_dir, f)) for f in RSTGCN_FILES):
        print("downloading RSTGCN data (~45 MB)...")
        data = urllib.request.urlopen(RSTGCN_ZIP, timeout=300).read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                base = os.path.basename(name)
                if base in RSTGCN_FILES:
                    with open(os.path.join(raw_dir, base), "wb") as f:
                        f.write(z.read(name))
    st = os.path.join(raw_dir, "stations.json")
    if not os.path.exists(st):
        print("downloading datameet stations.json...")
        urllib.request.urlretrieve(DATAMEET_STATIONS, st)


def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


def clock(s):
   
    t = pd.to_datetime(s, format="%I:%M %p")
    return t.hour * 60 + t.minute


WORDS = {
    "Raj": "Rajdhani",
    "Exp": "Express",
    "Expres": "Express",
    "Spl": "Special",
    "Sf": "SF",
    "Garibrath": "Garib Rath",
    "Jan": "Jan",
    "Shtbdi": "Shatabdi",
    "Shtb": "Shatabdi",
    "Pass": "Passenger",
    "Ac": "AC",
    "Ii": "II",
}


def tidy_name(name, codes):
    
    words = str(name).replace("-", " - ").split()
    out = []
    for i, w in enumerate(words):
        if (
            w.upper() in codes
            and len(w) <= 5
            and w.lower() not in ("raj", "jan", "garib", "pass")
        ):
            out.append(w.upper())
        elif w in WORDS:
            out.append(WORDS[w])
        elif w == "M" and i == len(words) - 1:
            out.append("Mail")
        else:
            out.append(w)
    return " ".join(out).replace(" - ", "-")


def train_type(name, number):
    n = name.lower()
    for key, label in [
        ("vande", "Vande Bharat"),
        ("rajdhani", "Rajdhani"),
        ("shatabdi", "Shatabdi"),
        ("duronto", "Duronto"),
        ("garib", "Garib Rath"),
        ("humsafar", "Humsafar"),
        ("tejas", "Tejas"),
        ("sampark", "Sampark Kranti"),
        ("memu", "MEMU"),
        ("demu", "DEMU"),
        ("passenger", "Passenger"),
        ("mail", "Mail"),
        ("superfast", "Superfast"),
        ("sf ", "Superfast"),
    ]:
        if key in n:
            return label
    if str(number).startswith("0"):
        return "Special"
    return "Express"


def build(raw_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    routes = pd.read_csv(os.path.join(raw_dir, "train_routes_Sep2024.csv"))
    edges = pd.read_csv(os.path.join(raw_dir, "IRN_edges.csv"))
    zones = json.load(open(os.path.join(raw_dir, "stations_zones_mapping.json")))
    delays = pd.read_csv(
        os.path.join(raw_dir, "train_routes_delays_Sep2024.csv"),
        usecols=["train", "date", "station", "sch_arr", "sch_dep"],
    )
    dm = json.load(open(os.path.join(raw_dir, "stations.json")))["features"]

    
    und = {}
    for a, b, km, n in edges[["from", "to", "distance", "ntrains"]].itertuples(
        index=False
    ):
        if a == b or km <= 0:
            continue
        key = tuple(sorted((a, b)))
        if key not in und or km < und[key][0]:
            und[key] = [km, n]
        else:
            und[key][1] = max(und[key][1], n)
    neigh = defaultdict(dict)
    for (a, b), (km, n) in und.items():
        neigh[a][b] = km
        neigh[b][a] = km

    #stations&coordinates
    names = (
        routes.drop_duplicates("station_code")
        .set_index("station_code")["station_name"]
        .to_dict()
    )
    codes = set(names) | set(neigh)
    dm_coords = {}
    for f in dm:
        if f["geometry"]:
            lon, lat = f["geometry"]["coordinates"][:2]
            if (
                6 <= lat <= 37.5 and 68 <= lon <= 98
            ):  
                dm_coords[f["properties"]["code"]] = (lat, lon)

    coords, source = {}, {}
    for c in codes:
        if c in dm_coords:
            coords[c], source[c] = dm_coords[c], "datameet"
        elif OLD_CODES.get(c) in dm_coords:
            coords[c], source[c] = dm_coords[OLD_CODES[c]], "datameet (old code)"

   
    bad = []
    for c, p in coords.items():
        near = [(n, km) for n, km in neigh[c].items() if n in coords]
        if len(near) >= 2 and all(
            haversine(p, coords[n]) > max(3 * km, km + 80) for n, km in near
        ):
            bad.append(c)
    for c in bad:
        del coords[c]
        source[c] = "dropped"


    filled = 0
    changed = True
    while changed:
        changed = False
        for c in codes:
            if c in coords:
                continue
            near = [(coords[n], km) for n, km in neigh[c].items() if n in coords]
            if not near:
                continue
            w = [1 / max(km, 1) for _, km in near]
            lat = sum(p[0] * wi for (p, _), wi in zip(near, w)) / sum(w)
            lon = sum(p[1] * wi for (p, _), wi in zip(near, w)) / sum(w)
            coords[c] = (lat, lon)
            source[c] = "estimated from neighbours"
            filled += 1
            changed = True

    stop_count = routes.station_code.value_counts()
    st_rows = []
    for c in sorted(codes):
        if c not in coords:
            continue
        st_rows.append(
            {
                "code": c,
                "name": str(names.get(c, c)).title() if c in names else c,
                "lat": round(coords[c][0], 5),
                "lon": round(coords[c][1], 5),
                "zone": zones.get(c, ""),
                "trains": int(stop_count.get(c, 0)),
                "coord_source": source[c],
            }
        )
    stations = pd.DataFrame(st_rows)
    keep = set(stations.code)

    edge_rows = [
        {"a": a, "b": b, "km": km, "ntrains": n}
        for (a, b), (km, n) in und.items()
        if a in keep and b in keep
    ]

    #trains & stops
    routes = routes.sort_values(["trainNumber", "stnSerialNumber"])
    delays["weekday"] = pd.to_datetime(delays["date"]).dt.weekday

   
    def run_days(s):
        days = sorted(set(s))
        return "daily" if len(days) >= 5 else ",".join(str(d) for d in days)

    seen = (
        delays.drop_duplicates(["train", "date"])
        .groupby("train")["weekday"]
        .agg(run_days)
    )

    sched = (
        delays.dropna(subset=["sch_arr", "sch_dep"])
        .groupby(["train", "station"])[["sch_arr", "sch_dep"]]
        .agg(lambda x: x.mode().iloc[0])
    )

    def timings_ok(stops):
        if len(stops) < 2 or stops[-1]["arr"] <= stops[0]["dep"]:
            return False
        for a, b in zip(stops, stops[1:]):
            mins = b["arr"] - a["dep"]
            if b["km"] - a["km"] > 5 and (
                mins <= 0 or (b["km"] - a["km"]) / (mins / 60) > 160
            ):
                return False
        return True

    def make_stops(num, g, times):
        day = 0
        prev = None
        stops = []
        for i, row in enumerate(g.itertuples(index=False)):
            arr_s, dep_s = times(row)
            arr, dep = clock(arr_s), clock(dep_s)
            if prev is not None and arr < prev:  
                day += 1
            arr_abs = day * 1440 + arr
            if dep < arr:
                day += 1
            dep_abs = day * 1440 + dep
            prev = dep
            stops.append(
                {
                    "train": num,
                    "seq": i + 1,
                    "code": row.station_code,
                    "km": int(row.distance),
                    "arr": arr_abs,
                    "dep": dep_abs,
                    "day": day,
                }
            )
        return stops

    train_rows, stop_rows = [], []
    fixed = dropped = 0
    for num, g in routes.groupby("trainNumber"):
        g = g[g.station_code.isin(keep)]
        if len(g) < 2:
            continue
        stops = make_stops(num, g, lambda r: (r.arrivalTime, r.departureTime))
        if not timings_ok(stops):
            if all((num, c) in sched.index for c in g.station_code):
                stops = make_stops(
                    num, g, lambda r: tuple(sched.loc[(num, r.station_code)])
                )
            if timings_ok(stops):
                fixed += 1
            else:
                dropped += 1
                continue
        first, last = stops[0], stops[-1]
        name = tidy_name(g.trainName.iloc[0], codes)
        train_rows.append(
            {
                "number": num,
                "name": name,
                "type": train_type(name, num),
                "source": first["code"],
                "destination": last["code"],
                "departure": f"{first['dep'] % 1440 // 60:02d}:{first['dep'] % 60:02d}",
                "arrival": f"{last['arr'] % 1440 // 60:02d}:{last['arr'] % 60:02d}",
                "duration_min": last["arr"] - first["dep"],
                "distance_km": last["km"],
                "stops": len(stops),
                "run_days": seen.get(num, "daily"),
            }
        )
        stop_rows.extend(stops)

    stations.to_csv(os.path.join(out_dir, "stations.csv"), index=False)
    pd.DataFrame(edge_rows).to_csv(os.path.join(out_dir, "edges.csv"), index=False)
    pd.DataFrame(train_rows).to_csv(os.path.join(out_dir, "trains.csv"), index=False)
    pd.DataFrame(stop_rows).to_csv(os.path.join(out_dir, "stops.csv"), index=False)

    src = stations.coord_source.value_counts().to_dict()
    print(
        f"stations {len(stations)} | edges {len(edge_rows)} | trains {len(train_rows)} | stops {len(stop_rows)}"
    )
    print(f"coordinates: {src} (dropped as wrong: {len(bad)})")
    print(
        f"timetables: {fixed} fixed from the delay file, {dropped} trains dropped (no usable times)"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", help="folder that already has the raw files")
    args = ap.parse_args()
    raw = args.raw or RAW
    if not args.raw:
        try:
            download(raw)
        except Exception as e:
            sys.exit(
                f"download failed ({e}). Clone the two repos and pass --raw <folder>."
            )
    build(raw, OUT)
