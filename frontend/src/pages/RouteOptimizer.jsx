import { useEffect, useMemo, useRef, useState } from "react";
import api from "../api";
import NetworkMap from "../components/NetworkMap.jsx";
import StopStrip from "../components/StopStrip.jsx";
import StationPicker from "../components/StationPicker.jsx";
import Icon from "../components/Icon.jsx";
import WxIcon from "../components/WxIcon.jsx";
import {
  SEVERITY,
  ROUTE_COLORS,
  fmtMinutes,
  fmtTime,
  fmtDay,
  cssVar,
  sourceText,
} from "../lib/weather";
import {
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const STEPS = [
  "Find candidate routes",
  "Work out station ETAs",
  "Fetch forecasts",
  "Score weather risk",
  "Rank and explain",
];
const STEP_MS = 260;

function defaultDeparture() {
  const d = new Date(Date.now() + 60 * 60 * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
}

function riskColor(score) {
  return score >= 55
    ? "var(--danger)"
    : score >= 25
      ? "var(--warn)"
      : score > 0
        ? "var(--ok)"
        : "var(--surface-3)";
}

export default function RouteOptimizer() {
  const [network, setNetwork] = useState(null);
  const [overview, setOverview] = useState(null);
  const [source, setSource] = useState(null);
  const [destination, setDestination] = useState(null);
  const [departure, setDeparture] = useState(defaultDeparture);
  const [k, setK] = useState(4);

  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(null);
  const [step, setStep] = useState(-1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [zoom, setZoom] = useState(true);
  const resultsRef = useRef(null);

  useEffect(() => {
    api
      .get("/admin/network")
      .then((r) => setNetwork(r.data))
      .catch(() => {});
    api
      .get("/admin/weather-overview")
      .then((r) => setOverview(r.data))
      .catch(() => {});
  }, []);

  async function plan(e) {
    e?.preventDefault();
    if (!source || !destination) {
      setError("Pick a source and a destination from the list first.");
      return;
    }
    if (source.value === destination.value) {
      setError("Pick two different stations.");
      return;
    }
    setError("");
    setBusy(true);
    setResult(null);
    setSelected(null);
    let s = 0;
    setStep(0);
    const timer = setInterval(
      () => setStep((s = Math.min(s + 1, STEPS.length - 1))),
      STEP_MS,
    );
    // the API answers in ~10ms so the steps would just flash.
    // wait a bit so you can actually see them tick through
    const minDelay = new Promise((r) =>
      setTimeout(r, STEP_MS * (STEPS.length - 1)),
    );
    try {
      const [res] = await Promise.all([
        api.post("/admin/weather-route", {
          source: source.value,
          destination: destination.value,
          departure,
          k: Number(k),
        }),
        minDelay,
      ]);
      if (!res.data.routes.length) {
        setError("No route exists between these stations.");
      } else {
        setResult(res.data);
        setSelected(res.data.recommended_index);
        setTimeout(
          () =>
            resultsRef.current?.scrollIntoView({
              behavior: "smooth",
              block: "start",
            }),
          60,
        );
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Route planning failed");
    } finally {
      clearInterval(timer);
      setStep(STEPS.length);
      setBusy(false);
    }
  }

  // before planning the map shows weather right now, after planning it shows
  // the forecast at the time the train reaches each station
  const stationWeather = useMemo(() => {
    const out = {};
    if (result && selected != null) {
      result.routes[selected].stops.forEach(
        (s) =>
          (out[s.code] = {
            name: s.city,
            slot: s.forecast,
            risk: s.risk,
            eta: s.eta,
          }),
      );
    } else if (overview) {
      overview.stations.forEach(
        (s) => (out[s.code] = { name: s.city, slot: s.current, risk: s.risk }),
      );
    }
    return out;
  }, [result, selected, overview]);

  const routes = result?.routes || [];
  const best = result ? routes[result.recommended_index] : null;
  const shortest = result ? routes[result.shortest_index] : null;
  const sel = result && selected != null ? routes[selected] : null;
  const selColor =
    selected != null
      ? ROUTE_COLORS[selected % ROUTE_COLORS.length]
      : "var(--brand)";

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Route planner</div>
          <h1 className="page-title">
            {result
              ? `${result.source_name} to ${result.destination_name}`
              : "Plan a weather-aware route"}
          </h1>
          <p className="page-sub">
            Checks the forecast at each station for the time the train gets
            there, then picks the route that arrives first.
          </p>
        </div>
        {overview && (
          <span className="badge neutral">
            Weather source:{" "}
            {sourceText(result?.weather_source || overview.weather_source)}
          </span>
        )}
      </div>

      <form className="card" onSubmit={plan} style={{ marginBottom: 16 }}>
        <div className="planner-form">
          <StationPicker
            id="src"
            label="From"
            value={source}
            onChange={setSource}
            placeholder="Search source"
          />
          <button
            type="button"
            className="swap-btn"
            onClick={() => {
              setSource(destination);
              setDestination(source);
            }}
            aria-label="Swap stations"
            title="Swap stations"
          >
            <Icon name="swap" />
          </button>
          <StationPicker
            id="dst"
            label="To"
            value={destination}
            onChange={setDestination}
            placeholder="Search destination"
          />
          <div className="form-row wide">
            <label htmlFor="dep">Departure</label>
            <input
              id="dep"
              type="datetime-local"
              value={departure}
              onChange={(e) => setDeparture(e.target.value)}
              required
            />
          </div>
          <div className="form-row">
            <label htmlFor="k">Alternatives</label>
            <select id="k" value={k} onChange={(e) => setK(e.target.value)}>
              {[2, 3, 4, 5, 6].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <button className="btn accent" disabled={busy}>
            {busy ? "Planning…" : "Plan route"}
          </button>
        </div>
        {step >= 0 && step < STEPS.length && (
          <div className="progress-steps" aria-live="polite">
            {STEPS.map((s, i) => (
              <span
                key={s}
                className={i < step ? "done" : i === step ? "active" : ""}
              >
                {i < step ? (
                  <Icon name="check" size={13} />
                ) : (
                  <span
                    className="dot"
                    style={{ background: "currentColor" }}
                  />
                )}
                {s}
              </span>
            ))}
          </div>
        )}
      </form>

      {error && (
        <div className="msg error">
          <Icon name="alert" />
          {error}
        </div>
      )}

      <div ref={resultsRef} style={{ scrollMarginTop: 16 }} />

      {best && (
        <div className="grid cols-4" style={{ marginBottom: 16 }}>
          <div className="kpi">
            <div className="k">Recommended</div>
            <div className="v">Route {best.label}</div>
            <div className="s">
              {best.via.length ? `via ${best.via.join(", ")}` : "Direct"}
            </div>
          </div>
          <div className="kpi">
            <div className="k">Expected arrival</div>
            <div className="v mono">
              {fmtDay(best.arrival).split(",")[0]} {fmtTime(best.arrival)}
            </div>
            <div className="s">{fmtMinutes(best.adjusted_minutes)} journey</div>
          </div>
          <div className="kpi">
            <div className="k">Weather delay</div>
            <div className="v mono">
              {best.weather_delay_minutes
                ? `+${fmtMinutes(best.weather_delay_minutes)}`
                : "0 min"}
            </div>
            <div className={`s ${best.weather_delay_minutes ? "" : "ok"}`}>
              {best.stops.filter((s) => !s.risk.delay_minutes).length} of{" "}
              {best.stops.length} stations calm
            </div>
          </div>
          <div className="kpi">
            <div className="k">Versus shortest route</div>
            <div className="v mono">
              {result.time_saved_minutes > 0
                ? `−${fmtMinutes(result.time_saved_minutes)}`
                : "Same route"}
            </div>
            <div className="s">
              {best.is_shortest
                ? "Shortest is also safest"
                : `+${best.distance_km - shortest.distance_km} km distance`}
            </div>
          </div>
        </div>
      )}

      {/* map + alerts before planning, just the map after */}
      <div
        className={result ? "" : "split"}
        style={{ marginBottom: 16, alignItems: "start" }}
      >
        <section className="card flush">
          <div className="card-head">
            <h3>
              {result
                ? `Route ${sel?.label}, forecast at each stop's ETA`
                : `Network now, ${network?.stations.length.toLocaleString() ?? ""} stations`}
            </h3>
            {result ? (
              <button
                className="btn ghost small"
                onClick={() => setZoom((z) => !z)}
              >
                {zoom ? "Show all of India" : "Zoom to route"}
              </button>
            ) : (
              <span className="hint">Hover a station for details</span>
            )}
          </div>
          <div
            style={{
              padding: "4px 8px 0",
              maxWidth: result ? 860 : undefined,
              margin: "0 auto",
            }}
          >
            <NetworkMap
              network={network}
              routes={routes.map((r) => ({ path: r.path }))}
              selected={selected}
              stationWeather={stationWeather}
              fit={zoom && result ? "route" : "all"}
            />
          </div>
          {result && (
            <div className="map-legend">
              {routes.map((r, i) => (
                <button
                  key={i}
                  onClick={() => setSelected(i)}
                  aria-pressed={selected === i}
                >
                  <span
                    className="sw"
                    style={{
                      background: ROUTE_COLORS[i % ROUTE_COLORS.length],
                    }}
                  />
                  <span
                    style={{
                      fontWeight: selected === i ? 600 : 400,
                      color: selected === i ? "var(--text)" : undefined,
                    }}
                  >
                    Route {r.label}
                    {r.is_recommended ? " (recommended)" : ""}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>

        {!result && <WeatherAlerts overview={overview} />}
      </div>

      {result && (
        <>
          <section className="card flush" style={{ marginBottom: 16 }}>
            <div className="card-head">
              <h3>Candidate routes</h3>
              <span className="hint">Select a row to inspect it</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Route</th>
                    <th>Via</th>
                    <th className="r">Distance</th>
                    <th className="r">Clear-weather time</th>
                    <th className="r">Weather delay</th>
                    <th className="r">Journey</th>
                    <th>Risk</th>
                    <th>Worst stop</th>
                  </tr>
                </thead>
                <tbody>
                  {routes.map((r, i) => {
                    const worst = r.stops.reduce(
                      (w, s) =>
                        s.risk.delay_minutes > (w?.risk.delay_minutes ?? 0)
                          ? s
                          : w,
                      null,
                    );
                    return (
                      <tr
                        key={i}
                        className={`selectable ${selected === i ? "selected" : ""}`}
                        onClick={() => setSelected(i)}
                      >
                        <td style={{ whiteSpace: "nowrap" }}>
                          <button
                            className="btn ghost small"
                            style={{ padding: "0 6px", fontWeight: 600 }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelected(i);
                            }}
                          >
                            <span
                              className="dot"
                              style={{
                                background:
                                  ROUTE_COLORS[i % ROUTE_COLORS.length],
                              }}
                            />{" "}
                            {r.label}
                          </button>
                          {r.is_recommended && (
                            <span
                              className="badge brand"
                              style={{ marginLeft: 4 }}
                            >
                              Recommended
                            </span>
                          )}
                          {r.is_shortest && (
                            <span
                              className="badge neutral"
                              style={{ marginLeft: 4 }}
                            >
                              Shortest
                            </span>
                          )}
                        </td>
                        <td>{r.via.length ? r.via.join(", ") : "Direct"}</td>
                        <td className="r">
                          {r.distance_km.toLocaleString()} km
                        </td>
                        <td className="r">{fmtMinutes(r.base_minutes)}</td>
                        <td
                          className="r"
                          style={{
                            color:
                              r.weather_delay_minutes >= 60
                                ? "var(--danger)"
                                : r.weather_delay_minutes
                                  ? "var(--warn)"
                                  : "var(--muted)",
                            fontWeight:
                              r.weather_delay_minutes >= 60 ? 600 : 400,
                          }}
                        >
                          {r.weather_delay_minutes
                            ? `+${fmtMinutes(r.weather_delay_minutes)}`
                            : "-"}
                        </td>
                        <td
                          className="r"
                          style={{ fontWeight: r.is_recommended ? 600 : 400 }}
                        >
                          {fmtMinutes(r.adjusted_minutes)}
                        </td>
                        <td>
                          <div className="meter">
                            <div className="bar">
                              <i
                                style={{
                                  width: `${r.risk_score}%`,
                                  background: riskColor(r.risk_score),
                                }}
                              />
                            </div>
                            <span className="mono">{r.risk_score}</span>
                          </div>
                        </td>
                        <td>
                          {worst ? (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6,
                              }}
                            >
                              <WxIcon slot={worst.forecast} size={18} />
                              {worst.city} · {worst.forecast?.description}
                            </span>
                          ) : (
                            <span className="muted">None</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {sel && (
            <section className="card" style={{ marginBottom: 16 }}>
              <div className="card-head">
                <h3>Stops on route {sel.label}</h3>
                <span className="hint">
                  Departs {fmtDay(result.departure)} {fmtTime(result.departure)}{" "}
                  · arrives {fmtDay(sel.arrival)} {fmtTime(sel.arrival)}
                </span>
              </div>
              <StopStrip stops={sel.stops} color={selColor} />
              {sel.stops.some((s) => s.risk.factors.length) && (
                <div className="table-wrap" style={{ marginTop: 12 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Station</th>
                        <th>ETA</th>
                        <th>Hazard</th>
                        <th className="r">Expected delay</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sel.stops
                        .filter((s) => s.risk.factors.length)
                        .flatMap((s) =>
                          s.risk.factors.map((f, j) => (
                            <tr key={s.code + f.label}>
                              <td>{j === 0 ? s.city : ""}</td>
                              <td className="mono">
                                {j === 0 ? fmtTime(s.eta) : ""}
                              </td>
                              <td>{f.label}</td>
                              <td className="r mono">+{f.minutes} min</td>
                            </tr>
                          )),
                        )}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          )}

          <div className="grid cols-2" style={{ marginBottom: 16 }}>
            <section className="card">
              <h3>Journey time by route</h3>
              <BreakdownChart routes={routes} />
            </section>
            <section className="card">
              <h3>Expected delay per station · route {sel?.label}</h3>
              {sel && <StationDelayChart route={sel} color={selColor} />}
            </section>
          </div>
        </>
      )}

      {result && (
        <DistanceAnalysis source={result.source} name={result.source_name} />
      )}
    </div>
  );
}

function WeatherAlerts({ overview }) {
  if (!overview)
    return (
      <div className="card">
        <div className="skeleton" style={{ height: 300 }} />
      </div>
    );
  const alerts = [...overview.stations]
    .sort((a, b) => b.risk.delay_minutes - a.risk.delay_minutes)
    .filter((s) => s.risk.delay_minutes > 0);
  return (
    <section className="card flush">
      <div className="card-head">
        <h3>Weather alerts now</h3>
        <span className="hint">
          {alerts.length} of {overview.stations.length} stations
        </span>
      </div>
      {alerts.length ? (
        <table>
          <thead>
            <tr>
              <th>Station</th>
              <th>Conditions</th>
              <th className="r">Impact</th>
            </tr>
          </thead>
          <tbody>
            {alerts.slice(0, 8).map((s) => (
              <tr key={s.code}>
                <td>{s.city}</td>
                <td>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 6,
                    }}
                  >
                    <WxIcon slot={s.current} size={18} />
                    <span style={{ textTransform: "capitalize" }}>
                      {s.current.description}
                    </span>
                  </span>
                </td>
                <td className="r">
                  <span className={`badge ${s.risk.severity}`}>
                    +{s.risk.delay_minutes} min
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="empty-state">
          <b>All stations are calm</b>No weather hazards on the network right
          now.
        </div>
      )}
    </section>
  );
}

function ChartTip({ active, payload, label, unit = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tooltip-box">
      <b>{label}</b>
      {payload.map((p) => (
        <div key={p.dataKey}>
          {p.name}: {p.value}
          {unit}
        </div>
      ))}
    </div>
  );
}

// ROUTE_COLORS are "var(--route-a)" etc, recharts needs the real hex
function resolve(color) {
  return color.startsWith("var(") ? cssVar(color.slice(4, -1)) : color;
}

function BreakdownChart({ routes }) {
  const axis = cssVar("--muted");
  const grid = cssVar("--border");
  const data = routes.map((r) => ({
    name: `Route ${r.label}`,
    base: +(r.base_minutes / 60).toFixed(1),
    delay: +(r.weather_delay_minutes / 60).toFixed(1),
  }));
  return (
    <ResponsiveContainer width="100%" height={230}>
      <BarChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis
          dataKey="name"
          stroke={axis}
          tick={{ fill: axis, fontSize: 12 }}
        />
        <YAxis stroke={axis} tick={{ fill: axis, fontSize: 11 }} unit="h" />
        <Tooltip
          content={<ChartTip unit=" h" />}
          cursor={{ fill: cssVar("--surface-2") }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar
          dataKey="base"
          name="Clear-weather time"
          stackId="t"
          fill={cssVar("--brand")}
          maxBarSize={56}
        />
        <Bar
          dataKey="delay"
          name="Weather delay"
          stackId="t"
          fill={cssVar("--danger")}
          maxBarSize={56}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

function StationDelayChart({ route, color }) {
  const axis = cssVar("--muted");
  const grid = cssVar("--border");
  const c = resolve(color);
  const data = route.stops.map((s) => ({
    city: s.city,
    delay: s.risk.delay_minutes,
    temp: Math.round(s.forecast?.temp ?? 0),
  }));
  return (
    <ResponsiveContainer width="100%" height={230}>
      <LineChart
        data={data}
        margin={{ top: 6, right: 8, bottom: 0, left: -12 }}
      >
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis
          dataKey="city"
          stroke={axis}
          tick={{ fill: axis, fontSize: 11 }}
        />
        <YAxis
          yAxisId="d"
          stroke={axis}
          tick={{ fill: axis, fontSize: 11 }}
          unit="m"
          allowDecimals={false}
        />
        <YAxis
          yAxisId="t"
          orientation="right"
          stroke={axis}
          tick={{ fill: axis, fontSize: 11 }}
          unit="°"
        />
        <Tooltip content={<ChartTip />} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          yAxisId="d"
          type="linear"
          dataKey="delay"
          name="Delay (min)"
          stroke={c}
          strokeWidth={2}
          dot={{ r: 4, fill: c }}
        />
        <Line
          yAxisId="t"
          type="linear"
          dataKey="temp"
          name="Temp (°C)"
          stroke={cssVar("--faint")}
          strokeDasharray="4 4"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// charts from the original minor project (plain Dijkstra, distance only)
function DistanceAnalysis({ source, name }) {
  const [open, setOpen] = useState(false);
  const [chart, setChart] = useState([]);
  useEffect(() => {
    if (!open || !source) return;
    api
      .get("/admin/optimization-chart", { params: { source } })
      .then((r) => setChart(r.data.points))
      .catch(() => setChart([]));
  }, [open, source]);
  const axis = cssVar("--muted");
  const grid = cssVar("--border");
  const ink = cssVar("--brand");
  return (
    <section className="card">
      <div className="card-head" style={{ marginBottom: open ? 12 : 0 }}>
        <h3>Dijkstra distances from {name} to the 30 busiest stations</h3>
        <button
          className="btn small"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          {open ? "Hide" : "Show"} charts
        </button>
      </div>
      {open && (
        <div className="grid cols-2">
          <ResponsiveContainer width="100%" height={260}>
            <ScatterChart
              margin={{ top: 10, right: 10, bottom: 20, left: -10 }}
            >
              <CartesianGrid stroke={grid} />
              <XAxis
                type="number"
                dataKey="distance"
                name="Distance"
                unit="km"
                stroke={axis}
                tick={{ fill: axis, fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="time"
                name="Time"
                unit="h"
                stroke={axis}
                tick={{ fill: axis, fontSize: 11 }}
              />
              <Tooltip cursor={{ stroke: axis }} />
              <Scatter name="Cities" data={chart} fill={ink} />
            </ScatterChart>
          </ResponsiveContainer>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart
              data={chart}
              margin={{ top: 10, right: 10, bottom: 20, left: -10 }}
            >
              <CartesianGrid stroke={grid} />
              <XAxis
                dataKey="city"
                stroke={axis}
                tick={{ fill: axis, fontSize: 10 }}
                angle={-30}
                textAnchor="end"
                height={60}
              />
              <YAxis stroke={axis} tick={{ fill: axis, fontSize: 11 }} />
              <Tooltip />
              <Line
                type="linear"
                dataKey="distance"
                name="Distance (km)"
                stroke={ink}
                strokeWidth={2}
                dot={{ fill: ink, r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
