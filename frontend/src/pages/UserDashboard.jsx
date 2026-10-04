import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth.jsx";
import Icon from "../components/Icon.jsx";
import JourneyForecast from "../components/JourneyForecast.jsx";
import TrainSearch from "../components/TrainSearch.jsx";
import { IRCTC_URL, todayISO, fmtDateOnly } from "../lib/weather";

export default function UserDashboard() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [network, setNetwork] = useState(null);
  const [next, setNext] = useState({ data: null, loading: false, error: "" });

  function loadTrips() {
    api
      .get("/user/tickets")
      .then((r) => setTickets(r.data))
      .catch(() => {});
  }

  useEffect(() => {
    loadTrips();
    api
      .get("/user/network")
      .then((r) => setNetwork(r.data))
      .catch(() => {});
  }, []);

  const confirmed = tickets.filter((t) => t.status === "CONFIRMED");
  const upcoming = useMemo(
    () =>
      tickets
        .filter((t) => t.status === "CONFIRMED" && t.booking_date >= todayISO())
        .sort((a, b) => a.booking_date.localeCompare(b.booking_date)),
    [tickets],
  );
  const nextTicket = upcoming[0];

  useEffect(() => {
    if (!nextTicket) return;
    setNext({ data: null, loading: true, error: "" });
    api
      .get(`/user/tickets/${nextTicket.ticket_id}/forecast`)
      .then((r) => setNext({ data: r.data, loading: false, error: "" }))
      .catch((e) =>
        setNext({
          data: null,
          loading: false,
          error: e.response?.data?.detail || "Couldn't load forecast",
        }),
      );
  }, [nextTicket?.ticket_id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Overview</div>
          <h1 className="page-title">Hello, {user?.username}</h1>
        </div>
      </div>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <div className="kpi">
          <div className="k">Upcoming journeys</div>
          <div className="v">{upcoming.length}</div>
          <div className="s">
            {nextTicket
              ? `Next on ${fmtDateOnly(nextTicket.booking_date)}`
              : "None saved yet"}
          </div>
        </div>
        <div className="kpi">
          <div className="k">Saved trips</div>
          <div className="v">{confirmed.length}</div>
          <div className="s">
            <Link to="/tickets">View all</Link>
          </div>
        </div>
      </div>

      <h3 className="section-title">Find a train</h3>
      <div style={{ marginBottom: 24 }}>
        <TrainSearch network={network} onSaved={loadTrips} />
      </div>

      <div className="card-head" style={{ marginBottom: 8 }}>
        <h3 style={{ margin: 0, fontSize: 15 }}>
          Your next journey
          {nextTicket && (
            <span className="muted" style={{ fontWeight: 400 }}>
              {" "}
              · {nextTicket.train_name || nextTicket.train_number}
            </span>
          )}
        </h3>
      </div>
      <div style={{ marginBottom: 16 }}>
        {nextTicket ? (
          <JourneyForecast
            data={next.data}
            loading={next.loading}
            error={next.error}
            network={network}
            showMap
            mapSide
          />
        ) : (
          <div className="card empty-state">
            <Icon name="ticket" size={28} />
            <b>No upcoming trips</b>
            <div>
              Search above, pick a train and press Save trip. The weather along
              the way shows up here.
            </div>
          </div>
        )}
      </div>

      {upcoming.length > 0 && (
        <section className="card flush">
          <div className="card-head">
            <h3>Upcoming trips</h3>
            <Link className="hint" to="/tickets">
              All saved trips <Icon name="chevron" size={12} />
            </Link>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Train</th>
                  <th>Journey</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {upcoming.map((t) => (
                  <tr key={t.ticket_id}>
                    <td className="mono">{fmtDateOnly(t.booking_date)}</td>
                    <td>
                      <span className="mono">{t.train_number}</span>{" "}
                      {t.train_name || ""}
                    </td>
                    <td>
                      {t.source_name || t.source} →{" "}
                      {t.destination_name || t.destination}
                    </td>
                    <td className="r">
                      <a
                        className="btn small"
                        href={IRCTC_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Book on IRCTC
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
