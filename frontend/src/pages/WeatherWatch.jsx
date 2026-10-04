import { useEffect, useMemo, useState } from "react";
import api from "../api";
import Icon from "../components/Icon.jsx";
import WxIcon from "../components/WxIcon.jsx";
import NetworkMap from "../components/NetworkMap.jsx";
import StationPicker from "../components/StationPicker.jsx";
import {
  SEVERITY,
  groupByDay,
  fmtTime,
  windKmh,
  visibilityText,
  cssVar,
} from "../lib/weather";
import {
  ComposedChart,
  Area,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

// rough risk for a whole day. Same thresholds as assess_slot() in route_planner.py
function dayRisk(day) {
  const s = day.slots;
  if (
    s.some(
      (x) =>
        x.condition === "Thunderstorm" ||
        x.visibility < 200 ||
        x.wind_speed >= 14,
    )
  )
    return "severe";
  if (s.some((x) => x.rain_mm >= 10 || x.visibility < 1000)) return "high";
  if (
    s.some((x) => x.rain_mm >= 2.5 || x.visibility < 3000 || x.wind_speed >= 10)
  )
    return "moderate";
  return "low";
}

// basically CLOUDY but for stations
export default function WeatherWatch() {
  const [network, setNetwork] = useState(null);
  const [overview, setOverview] = useState(null);
  const [city, setCity] = useState(null); // station code
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [openDay, setOpenDay] = useState(null);
  const [unit, setUnit] = useState("C");

  useEffect(() => {
    api
      .get("/admin/network")
      .then((r) => setNetwork(r.data))
      .catch(() => {});
    api
      .get("/admin/weather-overview")
      .then((r) => {
        setOverview(r.data);
        setCity((c) => c || r.data.stations[0]?.code);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!city) return;
    setData(null);
    setError("");
    setOpenDay(null);
    api
      .get(`/admin/weather/${encodeURIComponent(city)}`)
      .then((r) => setData(r.data))
      .catch((e) =>
        setError(e.response?.data?.detail || "Could not load forecast"),
      );
  }, [city]);

  const byCity = useMemo(
    () =>
      Object.fromEntries((overview?.stations || []).map((s) => [s.code, s])),
    [overview],
  );
  const stationWeather = useMemo(
    () =>
      Object.fromEntries(
        (overview?.stations || []).map((s) => [
          s.code,
          { name: s.city, slot: s.current, risk: s.risk },
        ]),
      ),
    [overview],
  );

  const t = (c) =>
    unit === "C" ? Math.round(c) : Math.round((c * 9) / 5 + 32);
  const days = useMemo(() => groupByDay(data?.slots), [data]);
  const weekMin = days.length ? Math.min(...days.map((d) => d.min)) : 0;
  const weekMax = days.length ? Math.max(...days.map((d) => d.max)) : 1;
  const cur = data?.current;
  const risk = byCity[city]?.risk || data?.risk;

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Station weather</div>
          <h1 className="page-title">
            {data ? data.city : "Loading…"}{" "}
            {data && (
              <span className="mono muted" style={{ fontSize: 16 }}>
                {data.code}
              </span>
            )}
          </h1>
        </div>
        <div className="seg" role="group" aria-label="Temperature unit">
          <button
            className={unit === "C" ? "on" : ""}
            onClick={() => setUnit("C")}
            aria-pressed={unit === "C"}
          >
            °C
          </button>
          <button
            className={unit === "F" ? "on" : ""}
            onClick={() => setUnit("F")}
            aria-pressed={unit === "F"}
          >
            °F
          </button>
        </div>
      </div>

      {error && (
        <div className="msg error">
          <Icon name="alert" />
          {error}
        </div>
      )}

      <div className="ww-layout">
        <section className="card flush">
          <div className="card-head">
            <h3>Busiest stations</h3>
            <span className="hint">{overview?.stations.length ?? ""}</span>
          </div>
          <div style={{ padding: "0 12px" }}>
            <StationPicker
              id="ww-search"
              label="Any other station"
              value={null}
              cities={false}
              onChange={(o) => setCity(o.value)}
            />
          </div>
          <div className="station-list">
            {(overview?.stations || []).map((s) => {
              return (
                <button
                  key={s.code}
                  className={city === s.code ? "on" : ""}
                  onClick={() => setCity(s.code)}
                  aria-current={city === s.code}
                >
                  {s ? <WxIcon slot={s.current} size={20} /> : <span />}
                  <span
                    style={{ display: "flex", alignItems: "center", gap: 6 }}
                  >
                    {s.city}
                    {s && s.risk.delay_minutes > 0 && (
                      <span
                        className="dot"
                        style={{ background: SEVERITY[s.risk.severity]?.color }}
                        title={SEVERITY[s.risk.severity]?.label}
                      />
                    )}
                  </span>
                  <span className="t">{s ? `${t(s.current.temp)}°` : ""}</span>
                </button>
              );
            })}
          </div>
        </section>

        <div className="stack">
          <section className="card">
            {cur ? (
              <div className="now">
                <div>
                  <div className="big">
                    <WxIcon slot={cur} size={64} />
                    <span className="temp">{t(cur.temp)}°</span>
                  </div>
                  <div className="cond">{cur.description}</div>
                  <div className="muted">
                    Feels like {t(cur.feels_like)}° · {data.lat.toFixed(2)}°N,{" "}
                    {data.lon.toFixed(2)}°E
                  </div>
                </div>
                <div className="metrics">
                  <div className="kpi inset">
                    <div className="k">Wind</div>
                    <div className="v">{windKmh(cur.wind_speed)} km/h</div>
                  </div>
                  <div className="kpi inset">
                    <div className="k">Humidity</div>
                    <div className="v">{cur.humidity}%</div>
                  </div>
                  <div className="kpi inset">
                    <div className="k">Visibility</div>
                    <div className="v">{visibilityText(cur.visibility)}</div>
                  </div>
                  <div className="kpi inset">
                    <div className="k">Chance of rain</div>
                    <div className="v">{Math.round(cur.pop * 100)}%</div>
                  </div>
                  {data.sunrise && (
                    <div className="kpi inset">
                      <div className="k">Sunrise</div>
                      <div className="v">
                        {fmtTime(new Date(data.sunrise * 1000).toISOString())}
                      </div>
                    </div>
                  )}
                  {data.sunset && (
                    <div className="kpi inset">
                      <div className="k">Sunset</div>
                      <div className="v">
                        {fmtTime(new Date(data.sunset * 1000).toISOString())}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="skeleton" style={{ height: 140 }} />
            )}
            {risk && (
              <div
                className={`msg ${risk.delay_minutes ? "error" : "success"}`}
                style={{ margin: "16px 0 0" }}
              >
                <Icon name={risk.delay_minutes ? "alert" : "check"} />
                <span>
                  {risk.delay_minutes ? (
                    <>
                      Trains passing now could lose about{" "}
                      <b>{risk.delay_minutes} min</b>:{" "}
                      {risk.factors.map((f) => f.label).join(", ")}.
                    </>
                  ) : (
                    "No weather hazards. Normal running expected."
                  )}
                </span>
              </div>
            )}
          </section>

          <div className="grid cols-2">
            <section className="card">
              <div className="card-head">
                <h3>Next 24 hours</h3>
                <span className="hint">temperature and rain</span>
              </div>
              {data ? (
                <HourlyChart slots={data.slots.slice(0, 9)} t={t} unit={unit} />
              ) : (
                <div className="skeleton" style={{ height: 220 }} />
              )}
            </section>
            <section className="card flush">
              <div className="card-head">
                <h3>Network</h3>
                <span className="hint">click a station</span>
              </div>
              <div style={{ padding: "0 8px 8px" }}>
                <NetworkMap
                  network={network}
                  stationWeather={stationWeather}
                  onSelectCity={setCity}
                  highlightCity={city}
                  labels={8}
                />
              </div>
            </section>
          </div>

          <section className="card flush">
            <div className="card-head">
              <h3>5-day forecast</h3>
              <span className="hint">select a day for 3-hour detail</span>
            </div>
            <div className="table-wrap">
              <table className="day-table">
                <thead>
                  <tr>
                    <th>Day</th>
                    <th></th>
                    <th>Conditions</th>
                    <th className="r">Rain</th>
                    <th>Range</th>
                    <th>Rail impact</th>
                  </tr>
                </thead>
                <tbody>
                  {days.map((d) => {
                    const left =
                      ((d.min - weekMin) / Math.max(1, weekMax - weekMin)) *
                      100;
                    const width =
                      ((d.max - d.min) / Math.max(1, weekMax - weekMin)) * 100;
                    const open = openDay === d.key;
                    const level = dayRisk(d);
                    return [
                      <tr
                        key={d.key}
                        className={`selectable ${open ? "selected" : ""}`}
                        onClick={() => setOpenDay(open ? null : d.key)}
                      >
                        <td>
                          <button
                            className="btn ghost small"
                            style={{ padding: "0 4px", fontWeight: 600 }}
                            aria-expanded={open}
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpenDay(open ? null : d.key);
                            }}
                          >
                            {d.date.toLocaleDateString([], {
                              weekday: "short",
                            })}{" "}
                            {d.date.getDate()}
                          </button>
                        </td>
                        <td className="wx">
                          <WxIcon slot={d.headline} size={22} />
                        </td>
                        <td style={{ textTransform: "capitalize" }}>
                          {d.headline.description}
                        </td>
                        <td className="r mono">
                          {d.rain > 0.5 ? `${d.rain.toFixed(0)} mm` : "-"}
                        </td>
                        <td>
                          <span className="range">
                            <span>{t(d.min)}°</span>
                            <span className="track">
                              <span
                                className="fill"
                                style={{
                                  left: `${left}%`,
                                  width: `${Math.max(width, 4)}%`,
                                }}
                              />
                            </span>
                            <span>{t(d.max)}°</span>
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${level}`}>
                            {SEVERITY[level].label}
                          </span>
                        </td>
                      </tr>,
                      open && (
                        <tr key={d.key + "-x"} className="expand-row">
                          <td colSpan="6" style={{ padding: "8px 16px 12px" }}>
                            <div className="slots">
                              {d.slots.map((s) => (
                                <div className="slot" key={s.dt}>
                                  <div className="muted">{fmtTime(s.time)}</div>
                                  <WxIcon slot={s} size={24} />
                                  <div className="st">{t(s.temp)}°</div>
                                  <div className="muted">
                                    {windKmh(s.wind_speed)} km/h
                                  </div>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ),
                    ];
                  })}
                  {!days.length && (
                    <tr>
                      <td colSpan="6">
                        <div className="skeleton" style={{ height: 160 }} />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function HourlyChart({ slots, t, unit }) {
  const axis = cssVar("--muted");
  const grid = cssVar("--border");
  const line = cssVar("--high");
  const rain = cssVar("--wx-rain");
  const data = slots.map((s) => ({
    time: fmtTime(s.time),
    temp: t(s.temp),
    feels: t(s.feels_like),
    rain: s.rain_mm,
  }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart
        data={data}
        margin={{ top: 8, right: 4, bottom: 0, left: -18 }}
      >
        <CartesianGrid stroke={grid} vertical={false} />
        <XAxis
          dataKey="time"
          stroke={axis}
          tick={{ fill: axis, fontSize: 11 }}
          interval={1}
        />
        <YAxis
          yAxisId="t"
          stroke={axis}
          tick={{ fill: axis, fontSize: 11 }}
          unit="°"
          domain={["dataMin - 2", "dataMax + 2"]}
        />
        <YAxis
          yAxisId="r"
          orientation="right"
          hide
          domain={[0, (max) => Math.max(10, max * 2)]}
        />
        <Tooltip
          formatter={(v, n) => (n === "Rain" ? `${v} mm` : `${v}°${unit}`)}
        />
        <Bar
          yAxisId="r"
          dataKey="rain"
          name="Rain"
          fill={rain}
          opacity={0.5}
          maxBarSize={28}
        />
        <Area
          yAxisId="t"
          type="monotone"
          dataKey="temp"
          name="Temp"
          stroke={line}
          strokeWidth={2}
          fill={line}
          fillOpacity={0.08}
        />
        <Area
          yAxisId="t"
          type="monotone"
          dataKey="feels"
          name="Feels like"
          stroke={axis}
          strokeDasharray="4 4"
          fill="none"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
