import NetworkMap from "./NetworkMap.jsx";
import StopStrip from "./StopStrip.jsx";
import Icon from "./Icon.jsx";
import WxIcon from "./WxIcon.jsx";
import {
  SEVERITY,
  fmtMinutes,
  fmtTime,
  fmtDay,
  sourceText,
} from "../lib/weather";

const HEADLINE = {
  low: "Clear run expected",
  moderate: "Minor weather on the way",
  high: "Weather may delay this train",
  severe: "Severe weather on this route",
  unknown: "Journey weather",
};

// headline = model's prediction, badge = weather. they can disagree since the
// model has no weather in it yet
function modelHeadline(p50) {
  if (p50 < 10) return "Should run close to time";
  if (p50 < 30) return "Likely to be a little late";
  if (p50 < 60) return "Expect this train to run late";
  return "Likely to be well behind time";
}
const WEATHER_WORD = {
  low: "calm",
  moderate: "some rain",
  high: "bad",
  severe: "severe",
  unknown: "no data",
};

function AdvisoryIcon({ kind }) {
  const map = {
    storm: <WxIcon kind="storm" size={18} />,
    rain: <WxIcon kind="rain" size={18} />,
    fog: <WxIcon kind="fog" size={18} />,
    snow: <WxIcon kind="snow" size={18} />,
    wind: <Icon name="wind" size={16} style={{ color: "var(--muted)" }} />,
    heat: <Icon name="thermo" size={16} style={{ color: "var(--high)" }} />,
    water: <Icon name="drop" size={16} style={{ color: "var(--wx-rain)" }} />,
    jacket: <Icon name="jacket" size={16} style={{ color: "var(--muted)" }} />,
    umbrella: (
      <Icon name="umbrella" size={16} style={{ color: "var(--wx-rain)" }} />
    ),
    clock: <Icon name="clock" size={16} style={{ color: "var(--muted)" }} />,
    clear: <Icon name="check" size={16} style={{ color: "var(--ok)" }} />,
  };
  return (
    map[kind] || (
      <Icon name="alert" size={16} style={{ color: "var(--muted)" }} />
    )
  );
}

export default function JourneyForecast({
  data,
  loading,
  error,
  network,
  showMap = false,
  mapSide = false,
}) {
  if (loading && !data) {
    return (
      <div className="card">
        <div
          className="skeleton"
          style={{ height: 20, width: "45%", marginBottom: 14 }}
        />
        <div className="skeleton" style={{ height: 60, marginBottom: 14 }} />
        <div className="skeleton" style={{ height: 120 }} />
      </div>
    );
  }
  if (error)
    return (
      <div className="msg error">
        <Icon name="alert" />
        {error}
      </div>
    );
  if (!data) return null;

  if (data.reason === "route_unknown") {
    return (
      <div className="card empty-state">
        <Icon name="map" size={28} />
        <b>No weather coverage</b>
        We don't have forecasts for this route yet.
      </div>
    );
  }

  const sev = SEVERITY[data.severity] || SEVERITY.unknown;
  const from = data.board_name || data.path_names?.[0] || data.path[0];
  const to = data.alight_name || data.path_names?.at(-1) || data.path.at(-1);
  const fromModel = data.delay_source === "model";
  const sideways = mapSide && showMap && network;

  return (
    <div
      className={`card jf ${loading ? "is-loading" : ""} ${sideways ? "map-side" : ""}`}
    >
      <div className="jf-main">
        <div className="jf-top">
          <div>
            {data.train && (
              <div className="jf-train">
                {data.train.train_number} · {data.train.train_name}
              </div>
            )}
            <h3 className="jf-title">
              {!data.available
                ? HEADLINE.unknown
                : fromModel
                  ? modelHeadline(data.weather_delay_minutes)
                  : HEADLINE[data.severity] || HEADLINE.unknown}
            </h3>
            <div className="jf-route">
              {from} → {to} · {data.distance_km.toLocaleString()} km ·{" "}
              {fmtDay(data.departure)}
            </div>
          </div>
          {data.available && (
            <span className={`badge ${data.severity}`}>
              {fromModel
                ? `Weather: ${WEATHER_WORD[data.severity] || "no data"}`
                : sev.label}
            </span>
          )}
        </div>

        {data.note && (
          <div className="msg info">
            <Icon name="alert" />
            {data.note}
          </div>
        )}
        {data.status === "completed" && (
          <div className="msg info">
            <Icon name="clock" />
            This journey has finished, so no forecast is shown.
          </div>
        )}
        {!data.available && data.status === "upcoming" && (
          <div className="jf-wait">
            <Icon name="calendar" size={22} style={{ color: "var(--muted)" }} />
            <div>
              <b>Forecast not available yet</b>
              <div className="muted">
                Forecasts cover the next 5 days. Check back from{" "}
                <b>
                  {new Date(data.forecast_available_from).toLocaleDateString(
                    [],
                    { weekday: "short", day: "numeric", month: "short" },
                  )}
                </b>
                .
              </div>
            </div>
          </div>
        )}

        <div className="jf-kpis">
          <div className="kpi inset">
            <div className="k">Departs {from}</div>
            <div className="v">{fmtTime(data.departure)}</div>
          </div>
          <div className="kpi inset">
            <div className="k">Scheduled arrival</div>
            <div className="v">{fmtTime(data.scheduled_arrival)}</div>
            <div className="s">{fmtDay(data.scheduled_arrival)}</div>
          </div>
          {data.available && (
            <>
              <div className="kpi inset">
                <div className="k">
                  {fromModel ? "Expected delay" : "Possible weather delay"}
                </div>
                <div
                  className="v"
                  style={{
                    color:
                      data.weather_delay_minutes >= 30
                        ? "var(--danger)"
                        : data.weather_delay_minutes
                          ? "var(--warn)"
                          : "var(--ok)",
                  }}
                >
                  {data.weather_delay_minutes
                    ? `+${fmtMinutes(data.weather_delay_minutes)}`
                    : "None"}
                </div>
                {fromModel &&
                  data.delay_p90_minutes > data.weather_delay_minutes && (
                    <div className="s">
                      up to {fmtMinutes(data.delay_p90_minutes)} on a bad day
                    </div>
                  )}
              </div>
              <div className="kpi inset">
                <div className="k">Likely arrival</div>
                <div className="v">{fmtTime(data.expected_arrival)}</div>
                <div className="s">
                  {fmtDay(data.expected_arrival)}
                  {data.latest_arrival &&
                  data.latest_arrival !== data.expected_arrival
                    ? `, latest ${fmtTime(data.latest_arrival)}`
                    : ""}
                </div>
              </div>
            </>
          )}
        </div>

        {data.advisories?.length > 0 && (
          <ul className="advisories">
            {data.advisories.map((a, i) => (
              <li key={i}>
                <AdvisoryIcon kind={a.kind} />
                <span>{a.text}</span>
              </li>
            ))}
          </ul>
        )}

        <StopStrip stops={data.stops} />
      </div>

      {showMap && network && (
        <div className="jf-map">
          <NetworkMap
            network={network}
            routes={[{ path: data.path }]}
            selected={0}
            fit="route"
            stationWeather={Object.fromEntries(
              data.stops.map((s) => [
                s.code,
                { name: s.city, slot: s.forecast, risk: s.risk, eta: s.eta },
              ]),
            )}
          />
        </div>
      )}

      <div className="jf-foot">
        Weather: {sourceText(data.weather_source)}.{" "}
        {fromModel
          ? "Delay predicted by a model trained on real running data (Sept 2024)."
          : "Delay estimated from the weather alone (delay model not trained yet)."}
      </div>
    </div>
  );
}
