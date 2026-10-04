import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.getenv("RAILSKY_MODELS", os.path.join(ROOT, "models"))

_model = None
_loaded = False


class DelayModel:
    def __init__(self, folder):
        import lightgbm as lgb
        import pandas as pd

        self.pd = pd
        with open(os.path.join(folder, "metrics.json")) as f:
            self.meta = json.load(f)
        self.features = self.meta["features"]
        self.cats = self.meta["categories"]
        self.p50 = lgb.Booster(model_file=os.path.join(folder, "delay_p50.txt"))
        self.p90 = lgb.Booster(model_file=os.path.join(folder, "delay_p90.txt"))
        ts = pd.read_csv(os.path.join(folder, "hist_train_station.csv"))
        self.hist_ts = {(int(a), b): v for a, b, v in ts.itertuples(index=False)}
        self.hist_t = dict(
            pd.read_csv(os.path.join(folder, "hist_train.csv")).itertuples(index=False)
        )
        self.hist_s = dict(
            pd.read_csv(os.path.join(folder, "hist_station.csv")).itertuples(
                index=False
            )
        )

    def predict(self, train, rows):
        """rows: one dict per stop with seq, code, km, hour, weekday, traffic, zone and
        (if the model uses weather) precip/wind/thunder/temp. Returns [(p50, p90), ...]
        """
        pd = self.pd
        num = train["number"]
        records = []
        max_p = max_w = thunders = 0.0
        for r in rows:
            rec = {
                "seq": r["seq"],
                "km": r["km"],
                "station_traffic": r["traffic"],
                "zone": r["zone"],
                "hour": r["hour"],
                "weekday": r["weekday"],
                "ttype": train["type"],
                "hist_train_station": self.hist_ts.get((num, r["code"])),
                "hist_train": self.hist_t.get(num),
                "hist_station": self.hist_s.get(r["code"]),
            }
            if self.meta["uses_weather"]:
                p, w, th = r.get("precip"), r.get("wind"), r.get("thunder", 0.0)
                max_p = max(max_p, p or 0.0)
                max_w = max(max_w, w or 0.0)
                thunders += th
                rec.update(
                    precip=p,
                    wind=w,
                    thunder=th,
                    temp=r.get("temp"),
                    max_precip_so_far=max_p,
                    max_wind_so_far=max_w,
                    thunder_so_far=thunders,
                )
            records.append(rec)
        X = pd.DataFrame(records)[self.features]
        for c, cats in self.cats.items():
            col = X[c].astype(str)
            X[c] = pd.Categorical(
                col.where(col.isin(cats)), categories=cats
            )  # unseen -> missing
        lo = self.p50.predict(X)
        hi = self.p90.predict(X)
        return [(max(0.0, a), max(a, b)) for a, b in zip(lo, hi)]


def get_model():
    global _model, _loaded
    if not _loaded:
        _loaded = True
        if os.getenv("RAILSKY_NO_MODEL") != "1" and os.path.exists(
            os.path.join(MODEL_DIR, "delay_p50.txt")
        ):
            try:
                _model = DelayModel(MODEL_DIR)
            except Exception as e:  # missing lightgbm, half-written files etc
                print(f"delay model not loaded: {e}")
                _model = None
    return _model


def metrics():
    path = os.path.join(MODEL_DIR, "metrics.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
