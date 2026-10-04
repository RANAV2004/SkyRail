import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { downloadFile } from "../api";
import Icon from "../components/Icon.jsx";
import JourneyForecast from "../components/JourneyForecast.jsx";
import { IRCTC_URL, fmtDateOnly, todayISO } from "../lib/weather";

export default function MyTickets() {
  const [tickets, setTickets] = useState([]);
  const [message, setMessage] = useState(null);
  const [openWx, setOpenWx] = useState(null);
  const [wx, setWx] = useState({});

  function load() {
    api
      .get("/user/tickets")
      .then((r) => setTickets(r.data))
      .catch(() => {});
  }
  useEffect(() => {
    load();
  }, []);

  function toggleWeather(id) {
    if (openWx === id) {
      setOpenWx(null);
      return;
    }
    setOpenWx(id);
    if (wx[id]?.data) return;
    setWx((w) => ({ ...w, [id]: { loading: true } }));
    api
      .get(`/user/tickets/${id}/forecast`)
      .then((r) => setWx((w) => ({ ...w, [id]: { data: r.data } })))
      .catch((e) =>
        setWx((w) => ({
          ...w,
          [id]: { error: e.response?.data?.detail || "Couldn't load forecast" },
        })),
      );
  }

  async function remove(id) {
    if (!window.confirm("Remove this trip from your list?")) return;
    try {
      await api.delete(`/user/tickets/${id}`);
      setMessage({ type: "success", text: "Trip removed." });
      if (openWx === id) setOpenWx(null);
      load();
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Couldn't remove the trip",
      });
    }
  }

  const today = todayISO();
  const active = tickets.filter((t) => t.status === "CONFIRMED");
  const removed = tickets.length - active.length;

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">My trips</div>
          <h1 className="page-title">Saved trips</h1>
          <p className="page-sub">
            Open the forecast before you travel. Tickets themselves are booked
            on IRCTC.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="btn small"
            onClick={() =>
              downloadFile("/user/tickets/export.csv", "my_trips.csv")
            }
          >
            <Icon name="download" size={14} /> Export CSV
          </button>
          <Link className="btn small accent" to="/find">
            <Icon name="search" size={14} /> Find trains
          </Link>
        </div>
      </div>

      {message && (
        <div className={`msg ${message.type}`}>
          <Icon name={message.type === "error" ? "alert" : "check"} />
          {message.text}
        </div>
      )}

      <div className="card flush">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Train</th>
                <th>Journey</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {active.map((t) => {
                const past = t.booking_date < today;
                return (
                  <Fragment key={t.ticket_id}>
                    <tr className={openWx === t.ticket_id ? "selected" : ""}>
                      <td className="mono">{fmtDateOnly(t.booking_date)}</td>
                      <td>
                        <span className="mono">{t.train_number}</span>{" "}
                        {t.train_name}
                      </td>
                      <td>
                        {t.source_name || t.source} →{" "}
                        {t.destination_name || t.destination}
                      </td>
                      <td>
                        {past ? (
                          <span className="badge neutral">Travelled</span>
                        ) : (
                          <span className="badge confirmed">Upcoming</span>
                        )}
                      </td>
                      <td>
                        <div
                          style={{ display: "flex", gap: 6, flexWrap: "wrap" }}
                        >
                          <button
                            className={`btn small ${openWx === t.ticket_id ? "accent" : ""}`}
                            onClick={() => toggleWeather(t.ticket_id)}
                            aria-expanded={openWx === t.ticket_id}
                          >
                            <Icon name="cloud" size={14} /> Forecast
                          </button>
                          {!past && (
                            <a
                              className="btn small"
                              href={IRCTC_URL}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Book on IRCTC
                            </a>
                          )}
                          <button
                            className="btn small ghost"
                            onClick={() => remove(t.ticket_id)}
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                    {openWx === t.ticket_id && (
                      <tr className="expand-row">
                        <td colSpan="5" style={{ padding: "4px 16px 16px" }}>
                          <JourneyForecast
                            data={wx[t.ticket_id]?.data}
                            loading={wx[t.ticket_id]?.loading}
                            error={wx[t.ticket_id]?.error}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
              {active.length === 0 && (
                <tr className="empty-row">
                  <td colSpan="5">
                    No saved trips. <Link to="/find">Find a train</Link> and
                    press Save trip.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {removed > 0 && (
        <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>
          {removed} removed trip{removed > 1 ? "s" : ""} not shown.
        </p>
      )}
    </div>
  );
}
