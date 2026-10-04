import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import Icon from "./Icon.jsx";
import WxIcon from "./WxIcon.jsx";
import JourneyForecast from "./JourneyForecast.jsx";
import StationPicker from "./StationPicker.jsx";
import {
  IRCTC_URL,
  fmtMinutes,
  fmtTime,
  fmtDateOnly,
  todayISO,
} from "../lib/weather";

// used on Find trains and the overview
export default function TrainSearch({ initial = {}, network, onSaved }) {
  const [from, setFrom] = useState(initial.from || null);
  const [to, setTo] = useState(initial.to || null);
  const [date, setDate] = useState(initial.date || todayISO(1));

  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(null);
  const [copied, setCopied] = useState(false);

  // coming from the timetable page, search straight away
  useEffect(() => {
    if (initial.from && initial.to) search();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function search(e) {
    e?.preventDefault();
    if (!from || !to) {
      setError("Pick a source and a destination from the list first.");
      return;
    }
    if (from.value === to.value) {
      setError("From and To are the same station.");
      return;
    }
    setBusy(true);
    setError("");
    setSaved(null);
    try {
      const r = await api.get("/user/train-search", {
        params: {
          source: from.value,
          destination: to.value,
          travel_date: date,
        },
      });
      setData(r.data);
      setSelected(0);
    } catch (err) {
      setError(err.response?.data?.detail || "Search failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveTrip(option) {
    setSaved(null);
    try {
      await api.post("/user/tickets", {
        train_number: option.train.train_number,
        source: option.board,
        destination: option.alight,
        booking_date: data.travel_date,
      });
      setSaved({
        ok: true,
        text: `Saved ${option.train.train_name} on ${fmtDateOnly(data.travel_date)} to My trips.`,
      });
      onSaved?.();
    } catch (err) {
      setSaved({
        ok: false,
        text: err.response?.data?.detail || "Couldn't save the trip",
      });
    }
  }

  function copyNumber(n) {
    navigator.clipboard
      ?.writeText(String(n))
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => {});
  }

  const results = data?.results || [];
  const pick = results[selected];
  // for the (+1 day) next to the arrival time
  const dayOffset = useMemo(() => {
    if (!pick) return 0;
    const a = new Date(pick.departure),
      b = new Date(pick.scheduled_arrival);
    return Math.round(
      (new Date(b.toDateString()) - new Date(a.toDateString())) / 86400000,
    );
  }, [pick]);

  return (
    <div>
      <form className="card" onSubmit={search} style={{ marginBottom: 16 }}>
        <div className="planner-form find">
          <StationPicker
            id="f-from"
            label="From"
            value={from}
            onChange={setFrom}
            placeholder="Search source"
          />
          <button
            type="button"
            className="swap-btn"
            onClick={() => {
              setFrom(to);
              setTo(from);
            }}
            aria-label="Swap stations"
            title="Swap stations"
          >
            <Icon name="swap" />
          </button>
          <StationPicker
            id="f-to"
            label="To"
            value={to}
            onChange={setTo}
            placeholder="Search destination"
          />
          <div className="form-row">
            <label htmlFor="f-date">Travel date</label>
            <input
              id="f-date"
              type="date"
              min={todayISO()}
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </div>
          <button className="btn accent" disabled={busy}>
            {busy ? (
              <span className="spinner" />
            ) : (
              <Icon name="search" size={14} />
            )}{" "}
            {busy ? "Searching…" : "Search trains"}
          </button>
        </div>
      </form>

      {error && (
        <div className="msg error">
          <Icon name="alert" />
          {error}
        </div>
      )}

      {busy && (
        <div className="card loading-card">
          <span className="spinner big" />
          Finding trains and checking the weather along the way…
        </div>
      )}

      {busy && (
        <div className="card loading-card">
          <span className="spinner big" />
          Finding trains and checking the weather along the way…
        </div>
      )}

      {!busy && data && results.length === 0 && (
        <div className="card empty-state">
          <Icon name="train" size={28} />
          <b>
            No direct trains from {data.source_name} to {data.destination_name}{" "}
            that day
          </b>
          Try another date, the whole city instead of one station, or look up a
          train in the <Link to="/trains">timetable</Link>.
        </div>
      )}

      {!busy && results.length > 0 && (
        <div className="find-layout">
          <section className="card flush">
            <div className="card-head">
              <h3>
                {results.length} train{results.length > 1 ? "s" : ""},{" "}
                {data.source_name} to {data.destination_name},{" "}
                {fmtDateOnly(data.travel_date)}
              </h3>
              {data.weather_source === "openweathermap" ? (
                <span
                  className="badge low"
                  title="Forecast from OpenWeatherMap"
                >
                  Live weather
                </span>
              ) : (
                <span
                  className="badge high"
                  title="Set OWM_API_KEY on the backend to get real forecasts"
                >
                  {data.weather_source === "demo"
                    ? "Demo weather"
                    : "Some weather is demo data"}
                </span>
              )}
            </div>
            <div className="result-list" role="listbox" aria-label="Trains">
              {results.map((r, i) => {
                const worst = r.stops.reduce(
                  (w, s) =>
                    s.risk.delay_minutes > (w?.risk.delay_minutes ?? 0) ? s : w,
                  null,
                );
                return (
                  <button
                    key={r.train.train_number}
                    role="option"
                    aria-selected={selected === i}
                    className={`result ${selected === i ? "on" : ""}`}
                    onClick={() => {
                      setSelected(i);
                      setSaved(null);
                    }}
                  >
                    <span className="rank">{r.rank}</span>
                    <span className="body">
                      <span className="name">
                        {r.train.train_name}{" "}
                        <span className="mono muted">
                          {r.train.train_number}
                        </span>
                      </span>
                      <span className="times mono">
                        {r.board} {fmtTime(r.departure)} → {r.alight}{" "}
                        {fmtTime(r.scheduled_arrival)}
                        <span className="muted">
                          {" "}
                          · {fmtMinutes(r.scheduled_minutes)}
                        </span>
                      </span>
                      <span className="tags">
                        {r.rank === 1 && (
                          <span className="badge brand">Best pick</span>
                        )}
                        {r.is_fastest_on_paper && (
                          <span className="badge neutral">
                            Fastest on timetable
                          </span>
                        )}
                        {r.is_calmest && (
                          <span className="badge low">Calmest weather</span>
                        )}
                      </span>
                      <span className="summary">
                        {worst?.forecast ? (
                          <WxIcon slot={worst.forecast} size={16} />
                        ) : null}
                        {r.summary}
                      </span>
                    </span>
                    <span className="delay">
                      {r.available ? (
                        r.weather_delay_minutes ? (
                          <span
                            className={`badge ${delayClass(r.weather_delay_minutes)}`}
                            title={`Could be up to ${fmtMinutes(r.delay_p90_minutes)} late`}
                          >
                            ~{fmtMinutes(r.weather_delay_minutes)} late
                          </span>
                        ) : (
                          <span className="badge low">On time</span>
                        )
                      ) : (
                        <span className="badge unknown">No forecast</span>
                      )}
                      <span className="mono muted" style={{ fontSize: 12 }}>
                        total {fmtMinutes(r.adjusted_minutes)}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {pick && (
            <div className="stack">
              <section className="card book-box">
                <div className="book-top">
                  <div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      Train number
                    </div>
                    <div className="train-no">
                      {pick.train.train_number}
                      <button
                        className="btn ghost small icon-only"
                        onClick={() => copyNumber(pick.train.train_number)}
                        title="Copy train number"
                        aria-label="Copy train number"
                      >
                        <Icon name={copied ? "check" : "ticket"} size={14} />
                      </button>
                    </div>
                    <div style={{ fontWeight: 600 }}>
                      {pick.train.train_name}
                    </div>
                  </div>
                  <div className="book-actions">
                    <a
                      className="btn accent"
                      href={IRCTC_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Book on IRCTC <Icon name="arrowRight" size={14} />
                    </a>
                    <button className="btn" onClick={() => saveTrip(pick)}>
                      Save trip
                    </button>
                  </div>
                </div>
                <dl className="irctc-steps">
                  <dt>From</dt>
                  <dd>
                    {pick.board_name}{" "}
                    <span className="mono muted">{pick.board}</span>
                  </dd>
                  <dt>To</dt>
                  <dd>
                    {pick.alight_name}{" "}
                    <span className="mono muted">{pick.alight}</span>
                  </dd>
                  <dt>Date</dt>
                  <dd>{fmtDateOnly(data.travel_date)}</dd>
                  <dt>Departs</dt>
                  <dd className="mono">{fmtTime(pick.departure)}</dd>
                  <dt>Arrives</dt>
                  <dd className="mono">
                    {fmtTime(pick.scheduled_arrival)}
                    {dayOffset > 0
                      ? ` (+${dayOffset} day${dayOffset > 1 ? "s" : ""})`
                      : ""}
                  </dd>
                </dl>
                <p
                  className="muted"
                  style={{ margin: "10px 0 0", fontSize: 13 }}
                >
                  IRCTC opens in a new tab. Log in, search {pick.board} to{" "}
                  {pick.alight} on the same date and pick train{" "}
                  {pick.train.train_number}.
                </p>
                {pick.why_first && (
                  <div className="msg info" style={{ margin: "12px 0 0" }}>
                    <Icon name="alert" />
                    {pick.why_first}
                  </div>
                )}
                {saved && (
                  <div
                    className={`msg ${saved.ok ? "success" : "error"}`}
                    style={{ margin: "12px 0 0" }}
                  >
                    <Icon name={saved.ok ? "check" : "alert"} />
                    <span>
                      {saved.text}{" "}
                      {saved.ok && <Link to="/tickets">View my trips</Link>}
                    </span>
                  </div>
                )}
              </section>
              <JourneyForecast data={pick} network={network} showMap />
            </div>
          )}
        </div>
      )}

      {data && results.length > 0 && (
        <p className="muted" style={{ fontSize: 12, marginTop: 12 }}>
          Timetables are from September 2024 and some trains have changed since,
          so check the times on IRCTC before you book.
        </p>
      )}
    </div>
  );
}

// colour for the expected delay: under 15 min is normal for Indian Railways
function delayClass(m) {
  return m >= 60 ? "severe" : m >= 30 ? "high" : m >= 15 ? "moderate" : "low";
}
