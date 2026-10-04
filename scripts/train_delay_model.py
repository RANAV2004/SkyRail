import argparse
import json
import os
import time

import lightgbm as lgb
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")
MODELS = os.path.join(ROOT, "models")

SPLIT_DATE = "2024-09-24"
MAX_DELAY = 720  

BASE_FEATURES = [
    "seq",
    "km",
    "station_traffic",
    "zone",
    "hour",
    "weekday",
    "ttype",
    "hist_train_station",
    "hist_train",
    "hist_station",
]
WEATHER_FEATURES = [
    "precip",
    "wind",
    "thunder",
    "temp",
    "max_precip_so_far",
    "max_wind_so_far",
    "thunder_so_far",
]
CATEGORICAL = ["zone", "ttype"]

PARAMS = dict(
    n_estimators=400,
    learning_rate=0.05,
    num_leaves=63,
    min_child_samples=50,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.9,
    verbose=-1,
)


def load(raw_dir, weather_path):
    t0 = time.time()
    d = pd.read_csv(
        os.path.join(raw_dir, "train_routes_delays_Sep2024.csv"),
        usecols=["train", "date", "station", "arr_delay"],
    )
    stops = pd.read_csv(os.path.join(PROCESSED, "stops.csv"))
    stations = pd.read_csv(os.path.join(PROCESSED, "stations.csv"))
    trains = pd.read_csv(os.path.join(PROCESSED, "trains.csv"))

    d = d.dropna(subset=["arr_delay"])
    d = d[(d.arr_delay >= 0) & (d.arr_delay <= MAX_DELAY)]
    d = d.merge(
        stops.rename(columns={"code": "station"}), on=["train", "station"], how="inner"
    )
    d = d.merge(
        trains[["number", "type"]].rename(columns={"number": "train", "type": "ttype"}),
        on="train",
    )
    d = d.merge(
        stations[["code", "zone", "trains", "lat", "lon"]].rename(
            columns={"code": "station", "trains": "station_traffic"}
        ),
        on="station",
    )
    d["date"] = pd.to_datetime(d["date"])
    d["weekday"] = d.date.dt.weekday
    d["hour"] = (d.arr % 1440) // 60
    d = d[d.seq > 1]  

    if weather_path:
        d = add_weather(d, weather_path)
    print(f"loaded {len(d):,} rows in {time.time() - t0:.0f}s")
    return d


def add_weather(d, path):
    w = pd.read_csv(path, parse_dates=["time"])
    # same 0.5 degree grid the fetch script used
    d["cell_lat"] = (d.lat * 2).round() / 2
    d["cell_lon"] = (d.lon * 2).round() / 2
    d["time"] = (d.date + pd.to_timedelta(d.arr, unit="m")).dt.floor("h")
    d = d.merge(w, on=["cell_lat", "cell_lon", "time"], how="left")
    d["thunder"] = d.code.between(95, 99).astype(float)
    d = d.sort_values(["train", "date", "seq"])
    g = d.groupby(["train", "date"])
    d["max_precip_so_far"] = g.precip.cummax()
    d["max_wind_so_far"] = g.wind.cummax()
    d["thunder_so_far"] = g.thunder.cumsum()
    print(f"weather matched for {d.precip.notna().mean():.0%} of rows")
    return d.drop(columns=["cell_lat", "cell_lon", "time", "code"])


def add_history(train_part, *frames):
    
    ts = (
        train_part.groupby(["train", "station"])
        .arr_delay.mean()
        .rename("hist_train_station")
    )
    t = train_part.groupby("train").arr_delay.mean().rename("hist_train")
    s = train_part.groupby("station").arr_delay.mean().rename("hist_station")
    out = []
    for f in frames:
        f = f.drop(
            columns=["hist_train_station", "hist_train", "hist_station"],
            errors="ignore",
        )
        f = (
            f.merge(ts, on=["train", "station"], how="left")
            .merge(t, on="train", how="left")
            .merge(s, on="station", how="left")
        )
        out.append(f)
    return out, (ts, t, s)


def prep(df, features, categories=None):
    X = df[features].copy()
    for c in CATEGORICAL:
        if c in X:
            X[c] = pd.Categorical(
                X[c], categories=categories[c] if categories else None
            )
    return X


def fit(X, y, alpha):
    m = lgb.LGBMRegressor(objective="quantile", alpha=alpha, **PARAMS)
    m.fit(X, y)
    return m


def evaluate(d, features):
    tr, te = d[d.date < SPLIT_DATE], d[d.date >= SPLIT_DATE]
    (tr, te), _ = add_history(tr, tr, te)
    cats = {c: sorted(tr[c].dropna().unique()) for c in CATEGORICAL}
    Xtr, Xte = prep(tr, features, cats), prep(te, features, cats)
    p50 = fit(Xtr, tr.arr_delay, 0.5).predict(Xte)
    p90_model = fit(Xtr, tr.arr_delay, 0.9)
    p90 = p90_model.predict(Xte)
    y = te.arr_delay.values
    mae = lambda p: float(np.mean(np.abs(y - p)))
    hist = (
        te.hist_train_station.fillna(te.hist_train)
        .fillna(te.hist_station)
        .fillna(tr.arr_delay.median())
    )
    return (
        {
            "train_rows": len(tr),
            "test_rows": len(te),
            "baseline_zero": mae(np.zeros(len(y))),
            "baseline_history": mae(hist.values),
            "model_p50": mae(np.clip(p50, 0, None)),
            "p90_coverage": float(np.mean(y <= p90)),
            "within_15_min": float(np.mean(np.abs(y - p50) <= 15)),
        },
        p50,
        te,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=RAW)
    ap.add_argument("--weather", help="CSV from scripts/fetch_weather_history.py")
    args = ap.parse_args()

    d = load(args.raw, args.weather)
    features = BASE_FEATURES + (WEATHER_FEATURES if args.weather else [])

    t0 = time.time()
    results, p50, te = evaluate(d, features)
    print(
        f"evaluated in {time.time() - t0:.0f}s: "
        + ", ".join(
            f"{k} {v:.3f}" if isinstance(v, float) else f"{k} {v}"
            for k, v in results.items()
        )
    )
    if args.weather:
        no_wx, _, _ = evaluate(d, BASE_FEATURES)
        results["model_p50_without_weather"] = no_wx["model_p50"]
        print(f"same model without weather: MAE {no_wx['model_p50']:.2f}")

   
    te = te.assign(err=np.abs(te.arr_delay.values - p50))
    by_type = te.groupby("ttype", observed=True).agg(
        rows=("err", "size"), mae=("err", "mean"), avg_delay=("arr_delay", "mean")
    )
    by_type = by_type[by_type.rows >= 500].sort_values("rows", ascending=False)

    # final models on the whole month
    (full,), (ts, t, s) = add_history(d, d)
    cats = {c: sorted(full[c].dropna().unique()) for c in CATEGORICAL}
    X = prep(full, features, cats)
    os.makedirs(MODELS, exist_ok=True)
    m50 = fit(X, full.arr_delay, 0.5)
    m90 = fit(X, full.arr_delay, 0.9)
    m50.booster_.save_model(os.path.join(MODELS, "delay_p50.txt"))
    m90.booster_.save_model(os.path.join(MODELS, "delay_p90.txt"))
    ts.reset_index().to_csv(os.path.join(MODELS, "hist_train_station.csv"), index=False)
    t.reset_index().to_csv(os.path.join(MODELS, "hist_train.csv"), index=False)
    s.reset_index().to_csv(os.path.join(MODELS, "hist_station.csv"), index=False)

    gain = m50.booster_.feature_importance("gain")
    importance = sorted(
        zip(features, (gain / gain.sum()).round(4).tolist()), key=lambda x: -x[1]
    )
    delay_hist = np.histogram(
        d.arr_delay.clip(upper=240), bins=[0, 5, 15, 30, 60, 120, 240.1]
    )[0]

    meta = {
        "features": features,
        "categories": {k: [str(v) for v in vals] for k, vals in cats.items()},
        "uses_weather": bool(args.weather),
        "median_delay": float(d.arr_delay.median()),
        "trained_on": {
            "rows": len(d),
            "trains": int(d.train.nunique()),
            "stations": int(d.station.nunique()),
            "from": str(d.date.min().date()),
            "to": str(d.date.max().date()),
        },
        "test_period": f"{SPLIT_DATE} to {d.date.max().date()}",
        "metrics": results,
        "importance": importance,
        "by_train_type": [
            {"type": k, **{c: round(float(v), 1) for c, v in r.items()}}
            for k, r in by_type.iterrows()
        ],
        "delay_buckets": {
            "labels": ["0-5", "5-15", "15-30", "30-60", "60-120", "120+"],
            "counts": [int(x) for x in delay_hist],
        },
    }
    with open(os.path.join(MODELS, "metrics.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("saved models/ and models/metrics.json")


if __name__ == "__main__":
    main()
