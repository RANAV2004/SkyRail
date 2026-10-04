import { useEffect, useState } from "react";
import api from "../api";
import Icon from "../components/Icon.jsx";
import { cssVar } from "../lib/weather";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

// readable names for the feature columns in train_delay_model.py
const FEATURE_NAMES = {
  hist_train_station: "This train's past delay at this station",
  hist_station: "Average delay at this station",
  hist_train: "This train's average delay",
  km: "Distance from origin",
  station_traffic: "Trains through the station",
  zone: "Railway zone",
  seq: "Stop number",
  hour: "Hour of day",
  ttype: "Train type",
  weekday: "Day of week",
  precip: "Rain at the station",
  wind: "Wind at the station",
  thunder: "Thunderstorm",
  temp: "Temperature",
  max_precip_so_far: "Heaviest rain so far on the trip",
  max_wind_so_far: "Strongest wind so far",
  thunder_so_far: "Storms so far",
};

const pct = (x) => `${Math.round(x * 100)}%`;

export default function DelayModel() {
  const [m, setM] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/admin/model")
      .then((r) => setM(r.data))
      .catch(() => setError("Couldn't load the model report"));
  }, []);

  if (error)
    return (
      <div className="container">
        <div className="msg error">
          <Icon name="alert" />
          {error}
        </div>
      </div>
    );
  if (!m)
    return (
      <div className="container">
        <div className="skeleton" style={{ height: 400 }} />
      </div>
    );

  if (!m.trained) {
    return (
      <div className="container">
        <div className="page-head">
          <div>
            <div className="eyebrow">Delay model</div>
            <h1 className="page-title">Not trained yet</h1>
          </div>
        </div>
        <div className="card">
          <p>
            The app is using the hand-written weather rules for delays. To train
            the model:
          </p>
          <pre className="code">
            python scripts/build_data.py{"\n"}python
            scripts/train_delay_model.py
          </pre>
        </div>
      </div>
    );
  }

  const r = m.metrics;
  const gain = Math.round((1 - r.model_p50 / r.baseline_history) * 100);
  const mae = [
    { name: "Always say on time", v: r.baseline_zero },
    { name: "Train's usual delay", v: r.baseline_history },
    { name: "LightGBM model", v: r.model_p50 },
  ];
  const axis = cssVar("--muted");
  const grid = cssVar("--border");
  const topImp = m.importance[0][1];

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Delay model</div>
          <h1 className="page-title">How late will the train be?</h1>
          <p className="page-sub">
            LightGBM trained on {m.trained_on.rows.toLocaleString()} real
            arrival records ({m.trained_on.trains.toLocaleString()} trains,
            September 2024). Tested on the last week, {m.test_period}, which the
            model never saw.
          </p>
        </div>
        <span className={`badge ${m.in_use ? "low" : "neutral"}`}>
          {m.in_use
            ? "In use for passenger forecasts"
            : "Trained but not loaded"}
        </span>
      </div>

      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <div className="kpi">
          <div className="k">Average error</div>
          <div className="v mono">{r.model_p50.toFixed(1)} min</div>
          <div className="s ok">
            {gain}% better than the train's usual delay
          </div>
        </div>
        <div className="kpi">
          <div className="k">Within 15 minutes</div>
          <div className="v mono">{pct(r.within_15_min)}</div>
          <div className="s">of test predictions</div>
        </div>
        <div className="kpi">
          <div className="k">"Up to" range holds</div>
          <div className="v mono">{pct(r.p90_coverage)}</div>
          <div className="s">aimed for 90%</div>
        </div>
        <div className="kpi">
          <div className="k">Typical delay</div>
          <div className="v mono">{m.median_delay} min</div>
          <div className="s">median in the data</div>
        </div>
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <section className="card">
          <h3>Average error on the test week (minutes, lower is better)</h3>
          <ResponsiveContainer width="100%" height={230}>
            <BarChart
              data={mae}
              layout="vertical"
              margin={{ top: 6, right: 30, bottom: 0, left: 40 }}
            >
              <CartesianGrid stroke={grid} horizontal={false} />
              <XAxis
                type="number"
                stroke={axis}
                tick={{ fill: axis, fontSize: 11 }}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke={axis}
                tick={{ fill: axis, fontSize: 12 }}
                width={130}
              />
              <Tooltip formatter={(v) => `${v.toFixed(1)} min`} />
              <Bar dataKey="v" name="Error" maxBarSize={28}>
                {mae.map((d, i) => (
                  <Cell
                    key={d.name}
                    fill={i === 2 ? cssVar("--brand") : cssVar("--surface-3")}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="muted" style={{ fontSize: 13 }}>
            The middle bar is the one to beat. Just guessing each train's usual
            delay at each station is already decent, so a model only counts if
            it does better than that.
          </p>
        </section>

        <section className="card">
          <h3>What the model looks at</h3>
          <ul className="imp-list">
            {m.importance.map(([f, v]) => (
              <li key={f}>
                <span>{FEATURE_NAMES[f] || f}</span>
                <span className="bar">
                  <i style={{ width: `${(v / topImp) * 100}%` }} />
                </span>
                <span className="mono muted">{pct(v)}</span>
              </li>
            ))}
          </ul>
          {!m.uses_weather && (
            <div className="msg info" style={{ margin: "12px 0 0" }}>
              <Icon name="alert" />
              <span>
                No weather in this version. Run{" "}
                <code>scripts/fetch_weather_history.py</code> and retrain with{" "}
                <code>--weather</code> to add it. Until then the weather on the
                forecast pages is shown next to the prediction but doesn't
                change it.
              </span>
            </div>
          )}
        </section>
      </div>

      <div className="grid cols-2">
        <section className="card flush">
          <div className="card-head">
            <h3>By train type</h3>
            <span className="hint">test week</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th className="r">Records</th>
                  <th className="r">Avg delay</th>
                  <th className="r">Avg error</th>
                </tr>
              </thead>
              <tbody>
                {m.by_train_type.map((t) => (
                  <tr key={t.type}>
                    <td>{t.type}</td>
                    <td className="r mono">
                      {Math.round(t.rows).toLocaleString()}
                    </td>
                    <td className="r mono">{t.avg_delay} min</td>
                    <td className="r mono">{t.mae} min</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card">
          <h3>How late trains actually were</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={m.delay_buckets.labels.map((l, i) => ({
                l: `${l} min`,
                n: m.delay_buckets.counts[i],
              }))}
              margin={{ top: 6, right: 8, bottom: 0, left: 10 }}
            >
              <CartesianGrid stroke={grid} vertical={false} />
              <XAxis
                dataKey="l"
                stroke={axis}
                tick={{ fill: axis, fontSize: 11 }}
              />
              <YAxis
                stroke={axis}
                tick={{ fill: axis, fontSize: 11 }}
                tickFormatter={(v) => `${Math.round(v / 1000)}k`}
              />
              <Tooltip formatter={(v) => v.toLocaleString()} />
              <Bar
                dataKey="n"
                name="Arrivals"
                fill={cssVar("--brand")}
                maxBarSize={48}
              />
            </BarChart>
          </ResponsiveContainer>
          <p className="muted" style={{ fontSize: 13 }}>
            Most arrivals are within 15 minutes, but there's a long tail of 2
            hour plus delays. Those are the ones the model gets most wrong,
            which is why the forecast shows an "up to" time as well.
          </p>
        </section>
      </div>
    </div>
  );
}
