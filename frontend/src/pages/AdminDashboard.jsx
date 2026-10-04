import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api, { downloadFile } from "../api";
import Icon from "../components/Icon.jsx";
import WxIcon from "../components/WxIcon.jsx";
import NetworkMap from "../components/NetworkMap.jsx";
import { SEVERITY, windKmh, sourceText } from "../lib/weather";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [users, setUsers] = useState([]);
  const [overview, setOverview] = useState(null);
  const [network, setNetwork] = useState(null);

  useEffect(() => {
    api
      .get("/admin/dashboard")
      .then((r) => setStats(r.data))
      .catch(() => {});
    api
      .get("/admin/tickets")
      .then((r) => setTickets(r.data))
      .catch(() => {});
    api
      .get("/admin/users")
      .then((r) => setUsers(r.data))
      .catch(() => {});
    api
      .get("/admin/weather-overview")
      .then((r) => setOverview(r.data))
      .catch(() => {});
    api
      .get("/admin/network")
      .then((r) => setNetwork(r.data))
      .catch(() => {});
  }, []);

  const stations = useMemo(
    () =>
      overview
        ? [...overview.stations].sort(
            (a, b) =>
              b.risk.delay_minutes - a.risk.delay_minutes ||
              a.city.localeCompare(b.city),
          )
        : [],
    [overview],
  );
  const alerts = stations.filter((s) => s.risk.delay_minutes >= 10);
  const confirmed = tickets.filter((t) => t.status === "CONFIRMED").length;
  const userName = Object.fromEntries(
    users.map((u) => [u.user_id, u.full_name || u.username]),
  );
  const stationWeather = Object.fromEntries(
    stations.map((s) => [
      s.code,
      { name: s.city, slot: s.current, risk: s.risk },
    ]),
  );

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Overview</div>
          <h1 className="page-title">Network status</h1>
        </div>
        <Link className="btn accent" to="/admin/optimizer">
          <Icon name="route" /> Plan a route
        </Link>
      </div>

      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <div className="kpi">
          <div className="k">Registered users</div>
          <div className="v">{stats?.total_users ?? "-"}</div>
          <div className="s">
            <Link to="/admin/users">View all</Link>
          </div>
        </div>
        <div className="kpi">
          <div className="k">Trains in service</div>
          <div className="v">{stats?.total_trains ?? "-"}</div>
          <div className="s">
            across {stats?.total_stations?.toLocaleString() ?? "-"} stations
          </div>
        </div>
        <div className="kpi">
          <div className="k">Saved trips</div>
          <div className="v">{confirmed}</div>
          <div className="s">
            {(stats?.total_tickets ?? 0) - confirmed} removed
          </div>
        </div>
        <div className="kpi">
          <div className="k">Stations with weather alerts</div>
          <div
            className="v"
            style={{ color: alerts.length ? "var(--danger)" : undefined }}
          >
            {overview ? alerts.length : "-"}
          </div>
          <div className={`s ${alerts.length ? "" : "ok"}`}>
            {overview
              ? alerts.length
                ? `of ${stations.length} stations`
                : "All clear"
              : ""}
          </div>
        </div>
      </div>

      <div className="split" style={{ marginBottom: 16 }}>
        <section className="card flush">
          <div className="card-head">
            <h3>Weather at the 20 busiest stations</h3>
            <span className="hint">
              {overview
                ? `${sourceText(overview.weather_source)} · refreshed every ${overview.cache.ttl_seconds / 60} min`
                : ""}
            </span>
          </div>
          <div
            className="table-wrap"
            style={{ maxHeight: 470, overflowY: "auto" }}
          >
            <table>
              <thead>
                <tr>
                  <th>Station</th>
                  <th>Now</th>
                  <th className="r">Temp</th>
                  <th className="r">Wind</th>
                  <th>Rail impact</th>
                </tr>
              </thead>
              <tbody>
                {overview
                  ? stations.map((s) => (
                      <tr key={s.code}>
                        <td style={{ fontWeight: 500 }}>{s.city}</td>
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
                        <td className="r mono">
                          {Math.round(s.current.temp)}°
                        </td>
                        <td className="r mono">
                          {windKmh(s.current.wind_speed)} km/h
                        </td>
                        <td>
                          <span className={`badge ${s.risk.severity}`}>
                            {s.risk.delay_minutes
                              ? `+${s.risk.delay_minutes} min`
                              : SEVERITY[s.risk.severity]?.label}
                          </span>
                        </td>
                      </tr>
                    ))
                  : Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i}>
                        <td colSpan="5">
                          <div className="skeleton" style={{ height: 18 }} />
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="card flush">
          <div className="card-head">
            <h3>Network map</h3>
            <Link to="/admin/weather" className="hint">
              Station details <Icon name="chevron" size={12} />
            </Link>
          </div>
          <div style={{ padding: "4px 8px 8px" }}>
            <NetworkMap network={network} stationWeather={stationWeather} />
          </div>
        </section>
      </div>

      <section className="card flush">
        <div className="card-head">
          <h3>Recently saved trips</h3>
          <button
            className="btn small"
            onClick={() =>
              downloadFile("/admin/tickets/export.csv", "all_bookings.csv")
            }
          >
            <Icon name="download" size={14} /> Export CSV
          </button>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Trip</th>
                <th>Passenger</th>
                <th>Train</th>
                <th>Journey</th>
                <th>Travel date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {tickets.slice(0, 10).map((t) => (
                <tr key={t.ticket_id}>
                  <td className="mono">#{t.ticket_id}</td>
                  <td>{userName[t.user_id] || `User ${t.user_id}`}</td>
                  <td className="mono">{t.train_number}</td>
                  <td>
                    {t.source_name || t.source} →{" "}
                    {t.destination_name || t.destination}
                  </td>
                  <td className="mono">{t.booking_date}</td>
                  <td>
                    <span
                      className={`badge ${t.status === "CONFIRMED" ? "confirmed" : "neutral"}`}
                    >
                      {t.status === "CONFIRMED" ? "Saved" : "Removed"}
                    </span>
                  </td>
                </tr>
              ))}
              {tickets.length === 0 && (
                <tr className="empty-row">
                  <td colSpan="6">No saved trips yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
