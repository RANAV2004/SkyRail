// CLOUDY used emoji here, svg looks better next to the other icons

function kindOf(slot) {
  if (!slot) return "partly";
  const hour = new Date(slot.dt * 1000).getHours();
  const night = hour < 6 || hour >= 19;
  switch (slot.condition) {
    case "Clear":
      return night ? "moon" : "sun";
    case "Clouds":
      return slot.condition_id <= 802 ? (night ? "cloud" : "partly") : "cloud";
    case "Rain":
    case "Drizzle":
      return "rain";
    case "Thunderstorm":
      return "storm";
    case "Snow":
      return "snow";
    case "Mist":
    case "Fog":
    case "Haze":
    case "Smoke":
    case "Dust":
      return "fog";
    default:
      return "partly";
  }
}

const CLOUD =
  "M7 18a4.5 4.5 0 0 1-.5-8.97A6 6 0 0 1 18 10.5a3.75 3.75 0 0 1 0 7.5z";
const SMALL_CLOUD =
  "M8 19a3.6 3.6 0 0 1-.4-7.18A4.8 4.8 0 0 1 16.8 12.4 3 3 0 0 1 16.8 19z";

export default function WxIcon({ slot, kind, size = 28, title }) {
  const k = kind || kindOf(slot);
  const label = title || slot?.description || k;
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    role: "img",
    "aria-label": label,
    className: "icon",
  };
  const cloudStyle = { stroke: "var(--wx-cloud)", fill: "var(--surface)" };

  switch (k) {
    case "sun":
      return (
        <svg {...common} style={{ stroke: "var(--wx-sun)" }}>
          <circle
            cx="12"
            cy="12"
            r="4.2"
            style={{ fill: "var(--wx-sun)", fillOpacity: 0.18 }}
          />
          <path d="M12 2.5v2M12 19.5v2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M2.5 12h2M19.5 12h2M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" />
        </svg>
      );
    case "moon":
      return (
        <svg {...common} style={{ stroke: "var(--wx-moon)" }}>
          <path
            d="M19.5 14.5A7.5 7.5 0 0 1 9.5 4.5a7.5 7.5 0 1 0 10 10z"
            style={{ fill: "var(--wx-moon)", fillOpacity: 0.12 }}
          />
        </svg>
      );
    case "partly":
      return (
        <svg {...common}>
          <g style={{ stroke: "var(--wx-sun)" }}>
            <circle cx="9" cy="9" r="3.2" />
            <path d="M9 2.8v1.4M3.6 9H2.2M4.6 4.6l1 1M13.4 4.6l-1 1" />
          </g>
          <path d={SMALL_CLOUD} style={cloudStyle} />
        </svg>
      );
    case "rain":
      return (
        <svg {...common}>
          <path
            d="M7 15a4.5 4.5 0 0 1-.5-8.97A6 6 0 0 1 18 7.5a3.75 3.75 0 0 1 0 7.5z"
            style={cloudStyle}
          />
          <path
            d="M8 18l-1 3M12 18l-1 3M16 18l-1 3"
            style={{ stroke: "var(--wx-rain)" }}
          />
        </svg>
      );
    case "storm":
      return (
        <svg {...common}>
          <path
            d="M7 14a4.5 4.5 0 0 1-.5-8.97A6 6 0 0 1 18 6.5a3.75 3.75 0 0 1 0 7.5z"
            style={cloudStyle}
          />
          <path
            d="M13 12.5l-3 5h4l-2.5 4.5"
            style={{ stroke: "var(--wx-bolt)", strokeWidth: 2 }}
          />
          <path
            d="M7.5 17l-.8 2M17 17l-.8 2"
            style={{ stroke: "var(--wx-rain)" }}
          />
        </svg>
      );
    case "snow":
      return (
        <svg {...common}>
          <path
            d="M7 15a4.5 4.5 0 0 1-.5-8.97A6 6 0 0 1 18 7.5a3.75 3.75 0 0 1 0 7.5z"
            style={cloudStyle}
          />
          <path
            d="M8 19h.01M12 20h.01M16 19h.01"
            style={{ stroke: "var(--wx-rain)", strokeWidth: 2.6 }}
          />
        </svg>
      );
    case "fog":
      return (
        <svg {...common} style={{ stroke: "var(--wx-cloud)" }}>
          <path d="M7 12a4.5 4.5 0 0 1 9.8-1.4" />
          <path d="M3 15h18M5 18.5h14M8 21.5h8" />
        </svg>
      );
    default:
      return (
        <svg {...common}>
          <path d={CLOUD} style={cloudStyle} />
        </svg>
      );
  }
}
