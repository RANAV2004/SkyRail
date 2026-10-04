import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import Icon from "../components/Icon.jsx";
import { fmtMinutes, todayISO } from "../lib/weather";

const PAGE = 50;
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function runDays(v) {
  if (v === "daily") return "Daily";
  return v
    .split(",")
    .map((d) => DAYS[Number(d)])
    .join(" ");
}

// ~3,800 trains is too many to send at once, so the search runs on the server
export default function Trains() {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const [data, setData] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      api
        .get("/user/trains", {
          params: {
            q: q.trim() || undefined,
            limit: PAGE,
            offset: page * PAGE,
          },
        })
        .then((r) => setData(r.data))
        .catch(() => setData({ total: 0, trains: [] }));
    }, 250);
    return () => clearTimeout(t);
  }, [q, page]);

  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE));

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Timetable</div>
          <h1 className="page-title">Trains</h1>
          <p className="page-sub">
            Timetables from September 2024. Press Forecast to check the weather
            for a trip tomorrow.
          </p>
        </div>
      </div>

      <section className="card flush">
        <div className="card-head">
          <h3>
            {data
              ? `${total.toLocaleString()} train${total === 1 ? "" : "s"}`
              : "Loading…"}
          </h3>
          <div style={{ position: "relative", width: 300 }}>
            <Icon
              name="search"
              size={14}
              style={{
                position: "absolute",
                left: 10,
                top: 13,
                color: "var(--muted)",
              }}
            />
            <label
              htmlFor="t-q"
              style={{
                position: "absolute",
                width: 1,
                height: 1,
                overflow: "hidden",
                clip: "rect(0 0 0 0)",
              }}
            >
              Search trains
            </label>
            <input
              id="t-q"
              placeholder="Name, number or station code"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(0);
              }}
              style={{ paddingLeft: 30 }}
            />
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Train</th>
                <th>Name</th>
                <th>From</th>
                <th>To</th>
                <th>Departs</th>
                <th>Arrives</th>
                <th className="r">Journey</th>
                <th>Runs</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(data?.trains || []).map((t) => (
                <tr key={t.train_number}>
                  <td className="mono">{t.train_number}</td>
                  <td style={{ fontWeight: 500 }}>
                    {t.train_name}
                    <div
                      className="muted"
                      style={{ fontSize: 12, fontWeight: 400 }}
                    >
                      {t.type}, {t.stops} stops,{" "}
                      {t.distance_km.toLocaleString()} km
                    </div>
                  </td>
                  <td>
                    {t.source_name}{" "}
                    <span className="mono muted">{t.source}</span>
                  </td>
                  <td>
                    {t.destination_name}{" "}
                    <span className="mono muted">{t.destination}</span>
                  </td>
                  <td className="mono">{t.departure}</td>
                  <td className="mono">{t.arrival}</td>
                  <td className="r mono">{fmtMinutes(t.duration_minutes)}</td>
                  <td style={{ fontSize: 12 }}>{runDays(t.run_days)}</td>
                  <td>
                    <Link
                      className="btn small"
                      to={`/find?from=${t.source}&fromName=${encodeURIComponent(t.source_name)}&to=${t.destination}&toName=${encodeURIComponent(t.destination_name)}&date=${todayISO(1)}`}
                    >
                      <Icon name="cloud" size={14} /> Forecast
                    </Link>
                  </td>
                </tr>
              ))}
              {data && total === 0 && (
                <tr className="empty-row">
                  <td colSpan="9">No trains match "{q}".</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {pages > 1 && (
          <div className="pager">
            <button
              className="btn small"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <span className="muted">
              Page {page + 1} of {pages}
            </span>
            <button
              className="btn small"
              disabled={page + 1 >= pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
