import json
import os
import time
import urllib.parse
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIONS = os.path.join(ROOT, "data", "processed", "stations.csv")
OUT = os.path.join(ROOT, "data", "raw", "weather_sep2024.csv")

URL = "https://archive-api.open-meteo.com/v1/archive"
START, END = "2024-09-01", "2024-10-04"  
BATCH = 50  


def cells():
    st = pd.read_csv(STATIONS)
    st = st[st.trains > 0]
    lat = (st.lat * 2).round() / 2
    lon = (st.lon * 2).round() / 2
    return sorted(set(zip(lat, lon)))


def fetch(batch):
    params = {
        "latitude": ",".join(str(a) for a, _ in batch),
        "longitude": ",".join(str(b) for _, b in batch),
        "start_date": START,
        "end_date": END,
        "hourly": "precipitation,wind_speed_10m,weather_code,temperature_2m",
        "timezone": "Asia/Kolkata",
    }
    url = URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                data = json.load(r)
            return (
                data if isinstance(data, list) else [data]
            )  # one location -> a dict, many -> a list
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"  failed ({e}), retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError("Open-Meteo kept failing, try again later")


def to_rows(batch, results):
    rows = []
    for (cell_lat, cell_lon), res in zip(batch, results):
        h = res["hourly"]
        for i, t in enumerate(h["time"]):
            rows.append(
                (
                    cell_lat,
                    cell_lon,
                    t,
                    h["precipitation"][i],
                    h["wind_speed_10m"][i],
                    h["weather_code"][i],
                    h["temperature_2m"][i],
                )
            )
    return rows


def main():
    todo = cells()
    print(f"{len(todo)} grid cells, {len(todo) // BATCH + 1} requests")
    rows = []
    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        rows += to_rows(batch, fetch(batch))
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)}")
        time.sleep(1)  # be nice to a free API
    df = pd.DataFrame(
        rows, columns=["cell_lat", "cell_lon", "time", "precip", "wind", "code", "temp"]
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"saved {len(df):,} rows to {OUT}")


if __name__ == "__main__":
    main()
