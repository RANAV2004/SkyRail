// groupByDay is from CLOUDY

export const SEVERITY = {
  low: { label: "Clear to run", color: "var(--ok)" },
  moderate: { label: "Minor delays", color: "var(--warn)" },
  high: { label: "Delays likely", color: "var(--high)" },
  severe: { label: "Severe disruption", color: "var(--danger)" },
  unknown: { label: "No data", color: "var(--muted)" },
};

export const ROUTE_COLORS = [
  "var(--route-a)",
  "var(--route-b)",
  "var(--route-c)",
  "var(--route-d)",
  "var(--route-e)",
  "var(--route-f)",
];

export function fmtMinutes(m) {
  m = Math.round(m || 0);
  const h = Math.floor(m / 60);
  const mm = m % 60;
  if (!h) return `${mm}m`;
  if (!mm) return `${h}h`;
  return `${h}h ${String(mm).padStart(2, "0")}m`;
}

export function fmtTime(iso) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtDay(iso) {
  return new Date(iso).toLocaleDateString([], {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function windKmh(ms) {
  return Math.round((ms || 0) * 3.6);
}

export function visibilityText(m) {
  if (m == null) return "-";
  return m >= 1000 ? `${(m / 1000).toFixed(m >= 10000 ? 0 : 1)} km` : `${m} m`;
}

// OWM gives 3-hour slots; this groups them into days for the 5-day table
export function groupByDay(slots) {
  const days = new Map();
  for (const s of slots || []) {
    const key = new Date(s.dt * 1000).toDateString();
    if (!days.has(key)) days.set(key, []);
    days.get(key).push(s);
  }
  return [...days.entries()].map(([key, list]) => {
    const temps = list.map((s) => s.temp);
    // the "headline" slot: worst weather of the day, else midday
    const rank = (s) =>
      (s.condition === "Thunderstorm" ? 50 : 0) +
      s.rain_mm * 2 +
      (s.visibility < 1000 ? 30 : 0);
    const worst = [...list].sort((a, b) => rank(b) - rank(a))[0];
    const midday =
      list.find((s) => new Date(s.dt * 1000).getHours() >= 12) || list[0];
    const headline = rank(worst) > 5 ? worst : midday;
    return {
      key,
      date: new Date(list[0].dt * 1000),
      min: Math.min(...temps),
      max: Math.max(...temps),
      rain: list.reduce((a, s) => a + s.rain_mm, 0),
      pop: Math.max(...list.map((s) => s.pop)),
      headline,
      slots: list,
    };
  });
}

// Recharts can't read CSS variables, so pass it the actual colour
export function cssVar(name, fallback = "#888") {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return v || fallback;
}

export const IRCTC_URL = "https://www.irctc.co.in/nget/train-search";

// "Fri, 2 Oct" style dates from a yyyy-mm-dd string, without timezone surprises
export function fmtDateOnly(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString([], {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function todayISO(offsetDays = 0) {
  const d = new Date(Date.now() + offsetDays * 86400000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// what the backend's weather_source means, in words
export function sourceText(src) {
  if (src === "openweathermap") return "OpenWeatherMap";
  if (src === "partial") return "OpenWeatherMap (some stations on demo data)";
  if (src === "demo-fallback") return "demo data (weather API not reachable)";
  return "demo data";
}
