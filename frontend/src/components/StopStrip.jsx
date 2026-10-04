import WxIcon from "./WxIcon.jsx";
import Icon from "./Icon.jsx";
import { SEVERITY, fmtTime, windKmh } from "../lib/weather";

export default function StopStrip({ stops, color = "var(--brand)" }) {
  return (
    <div
      className="strip"
      role="list"
      aria-label="Forecast at each station"
      style={{ "--route-line": color }}
    >
      {stops.map((s) => {
        const sev = SEVERITY[s.risk.severity] || SEVERITY.unknown;
        const pinColor = s.forecast ? sev.color : "var(--faint)";
        // model prediction on passenger trips, weather rules in the planner
        const late =
          s.predicted_delay != null ? s.predicted_delay : s.risk.delay_minutes;
        return (
          <div className="strip-stop" role="listitem" key={s.code || s.city}>
            <span className="pin" style={{ borderColor: pinColor }} />
            <div className="city">{s.city}</div>
            <div className="eta">
              {fmtTime(s.eta)} ·{" "}
              {new Date(s.eta).toLocaleDateString([], { weekday: "short" })}
            </div>
            {s.forecast ? (
              <>
                <div className="wx">
                  <WxIcon slot={s.forecast} size={32} />
                </div>
                <div className="temp">{Math.round(s.forecast.temp)}°</div>
                <div className="desc">{s.forecast.description}</div>
                <div className="meta">
                  <span title="Wind">
                    <Icon name="wind" size={11} />
                    {windKmh(s.forecast.wind_speed)}
                  </span>
                  <span title="Chance of rain">
                    <Icon name="drop" size={11} />
                    {Math.round(s.forecast.pop * 100)}%
                  </span>
                </div>
                {late > 0 && (
                  <span
                    className={`badge ${s.predicted_delay != null ? lateClass(late) : s.risk.severity}`}
                    title={
                      s.predicted_delay_p90
                        ? `up to ${s.predicted_delay_p90} min`
                        : undefined
                    }
                  >
                    +{late} min
                  </span>
                )}
              </>
            ) : (
              <div className="desc" style={{ marginTop: 10 }}>
                No forecast yet
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function lateClass(m) {
  return m >= 60 ? "severe" : m >= 30 ? "high" : m >= 10 ? "moderate" : "low";
}
