import { useMemo, useRef, useState } from "react";
import WxIcon from "./WxIcon.jsx";
import { SEVERITY, ROUTE_COLORS, fmtTime, windKmh } from "../lib/weather";

const W = 720;
const PAD = 28;

// network = /network response, stations are [code, name, lat, lon, trains]
export default function NetworkMap({
  network,
  routes = [],
  selected = null,
  stationWeather = {},
  onSelectCity,
  highlightCity,
  fit = "all",
  labels = 14,
}) {
  const [hover, setHover] = useState(null);
  const svgRef = useRef(null);

  const index = useMemo(() => {
    if (!network?.stations?.length) return null;
    const byCode = {};
    network.stations.forEach((s, i) => (byCode[s[0]] = i));
    return byCode;
  }, [network]);

  const sel = selected != null ? routes[selected] : null;
  const fitCodes = fit === "route" && sel ? sel.path : null;

  const proj = useMemo(() => {
    if (!index) return null;
    const list = fitCodes
      ? fitCodes.map((c) => network.stations[index[c]]).filter(Boolean)
      : network.stations;
    let minLat = Math.min(...list.map((s) => s[2])),
      maxLat = Math.max(...list.map((s) => s[2]));
    let minLon = Math.min(...list.map((s) => s[3])),
      maxLon = Math.max(...list.map((s) => s[3]));
    if (fitCodes) {
      // some room around the route, and not so zoomed in that it looks like a straight line
      const padLat = Math.max(0.6, (maxLat - minLat) * 0.15);
      const padLon = Math.max(0.6, (maxLon - minLon) * 0.15);
      minLat -= padLat;
      maxLat += padLat;
      minLon -= padLon;
      maxLon += padLon;
    }
    // 1 degree of longitude is shorter than 1 degree of latitude, without this India looks stretched
    const kx = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
    let scale = (W - PAD * 2) / ((maxLon - minLon) * kx);
    let H = (maxLat - minLat) * scale + PAD * 2;
    if (H > 640) {
      // tall routes (north to south): fit by height instead and centre sideways
      scale = (640 - PAD * 2) / (maxLat - minLat);
      H = 640;
    }
    const offX = (W - (maxLon - minLon) * kx * scale) / 2;
    const xy = (lat, lon) => [
      offX + (lon - minLon) * kx * scale,
      PAD + (maxLat - lat) * scale,
    ];
    const pts = network.stations.map((s) => xy(s[2], s[3]));
    return { pts, H: Math.round(Math.max(H, 260)) };
  }, [index, network, fitCodes]);

  // all 9,000 track sections as one path, much faster than 9,000 <line>s
  const railPath = useMemo(() => {
    if (!proj) return "";
    const p = proj.pts;
    return network.edges
      .map(
        ([a, b]) =>
          `M${p[a][0].toFixed(1)} ${p[a][1].toFixed(1)}L${p[b][0].toFixed(1)} ${p[b][1].toFixed(1)}`,
      )
      .join("");
  }, [proj, network]);

  const dotPath = useMemo(() => {
    if (!proj) return "";
    return proj.pts
      .map(([x, y]) => `M${x.toFixed(1)} ${y.toFixed(1)}h0`)
      .join("");
  }, [proj]);

  // names for the busiest stations, skipping any that would overlap one already placed
  const labelled = useMemo(() => {
    if (!proj || fitCodes || !labels) return [];
    const order = network.stations
      .map((s, i) => i)
      .sort((a, b) => network.stations[b][4] - network.stations[a][4]);
    const placed = [];
    for (const i of order) {
      if (placed.length >= labels) break;
      const [x, y] = proj.pts[i];
      if (
        placed.every(
          (j) => Math.hypot(proj.pts[j][0] - x, proj.pts[j][1] - y) > 55,
        )
      )
        placed.push(i);
    }
    return placed;
  }, [proj, network, fitCodes, labels]);

  if (!proj) return <div className="skeleton" style={{ height: 420 }} />;
  const { pts, H } = proj;
  const at = (code) => pts[index[code]];

  const pathD = (path) =>
    path
      .filter((c) => index[c] != null)
      .map(
        (c, i) =>
          `${i ? "L" : "M"}${at(c)[0].toFixed(1)},${at(c)[1].toFixed(1)}`,
      )
      .join(" ");

  const order = routes.map((_, i) => i).filter((i) => i !== selected);
  if (sel) order.push(selected);

  const endpoints = sel ? [sel.path[0], sel.path.at(-1)] : [];
  const marked = Object.keys(stationWeather).filter((c) => index[c] != null);

  function onMove(e) {
    const box = svgRef.current.getBoundingClientRect();
    const x = ((e.clientX - box.left) / box.width) * W;
    const y = ((e.clientY - box.top) / box.height) * H;
    // stations with weather are easier to hit than the small dots
    let best = null,
      bestD = 14;
    for (const c of marked) {
      const d = Math.hypot(at(c)[0] - x, at(c)[1] - y);
      if (d < bestD) {
        best = index[c];
        bestD = d;
      }
    }
    if (best == null) {
      bestD = 6;
      pts.forEach((p, i) => {
        const d = Math.hypot(p[0] - x, p[1] - y);
        if (d < bestD) {
          best = i;
          bestD = d;
        }
      });
    }
    setHover(best);
  }

  const hs = hover != null ? network.stations[hover] : null;
  const tip = hs && stationWeather[hs[0]];

  return (
    <div className="map-wrap">
      <svg
        ref={svgRef}
        className="net-map"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Rail network map"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        onClick={() => hs && onSelectCity?.(hs[0])}
        style={{ cursor: hs && onSelectCity ? "pointer" : "default" }}
      >
        <path d={railPath} className="rail" />
        <path d={dotPath} className="stn-dots" />

        {order.map((i) => {
          const r = routes[i];
          const color = ROUTE_COLORS[i % ROUTE_COLORS.length];
          const isSel = i === selected;
          const d = pathD(r.path);
          return (
            <g key={i + r.path.join("-")}>
              <path
                d={d}
                className={`route-line ${sel && !isSel ? "dim" : ""}`}
                strokeWidth={isSel ? 4 : 2.5}
                style={{ stroke: color }}
              />
              {isSel && (
                <circle
                  r="5"
                  strokeWidth="2"
                  style={{ fill: color, stroke: "var(--surface)" }}
                >
                  <animateMotion
                    dur={`${Math.min(16, Math.max(6, r.path.length / 6))}s`}
                    repeatCount="indefinite"
                    path={d}
                  />
                </circle>
              )}
            </g>
          );
        })}

        {labelled.map((i) => {
          const [x, y] = pts[i];
          const left = x > W - 120;
          return (
            <g
              key={"l" + i}
              className="node"
              transform={`translate(${x},${y})`}
            >
              <circle className="core" r="3" />
              <text x={left ? -7 : 7} y="4" textAnchor={left ? "end" : "start"}>
                {network.stations[i][1]}
              </text>
            </g>
          );
        })}

        {marked.map((code) => {
          const [x, y] = at(code);
          const w = stationWeather[code];
          const sev = w?.risk?.severity;
          const sevColor =
            sev && sev !== "unknown" ? SEVERITY[sev]?.color : null;
          const isEnd = endpoints.includes(code);
          const left = x > W - 130;
          return (
            <g
              key={code}
              className={`node on-route ${isEnd ? "endpoint" : ""}`}
              transform={`translate(${x},${y})`}
            >
              {(sev === "high" || sev === "severe") && (
                <circle className="halo" r="9" style={{ stroke: sevColor }} />
              )}
              <circle
                className="core"
                r={isEnd ? 6 : 4.5}
                style={
                  sevColor && !isEnd
                    ? { stroke: sevColor, strokeWidth: 2.5 }
                    : undefined
                }
              />
              {(fitCodes || isEnd || w.label) && (
                <text
                  x={left ? -9 : 9}
                  y="4"
                  textAnchor={left ? "end" : "start"}
                >
                  {w.name || network.stations[index[code]][1]}
                </text>
              )}
              {w.slot && (
                <g transform={`translate(${left ? -26 : 4},-26)`}>
                  <WxIcon slot={w.slot} size={18} />
                </g>
              )}
            </g>
          );
        })}

        {highlightCity && index[highlightCity] != null && (
          <circle
            cx={at(highlightCity)[0]}
            cy={at(highlightCity)[1]}
            r="10"
            fill="none"
            strokeWidth="2"
            style={{ stroke: "var(--brand)" }}
          />
        )}
      </svg>

      {hs && (
        <div
          className="map-tip"
          style={{
            left: `${(pts[hover][0] / W) * 100}%`,
            top: `${(pts[hover][1] / H) * 100}%`,
          }}
        >
          <b>{hs[1]}</b> <span className="mono muted">{hs[0]}</span>
          {tip?.slot ? (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginTop: 4,
                }}
              >
                <WxIcon slot={tip.slot} size={18} />
                <span className="mono">{Math.round(tip.slot.temp)}°C</span>
                <span style={{ textTransform: "capitalize" }}>
                  {tip.slot.description}
                </span>
              </div>
              <div className="muted">
                Wind {windKmh(tip.slot.wind_speed)} km/h, rain{" "}
                {tip.slot.rain_mm} mm
              </div>
              {tip.eta && (
                <div className="muted">Train gets here {fmtTime(tip.eta)}</div>
              )}
              {tip.risk && (
                <div
                  style={{
                    color: SEVERITY[tip.risk.severity]?.color,
                    marginTop: 4,
                    fontWeight: 600,
                  }}
                >
                  {SEVERITY[tip.risk.severity]?.label}
                  {tip.risk.delay_minutes
                    ? `, +${tip.risk.delay_minutes} min`
                    : ""}
                </div>
              )}
            </>
          ) : (
            <div className="muted">
              {hs[4]} train{hs[4] === 1 ? "" : "s"} stop here
              {onSelectCity ? ". Click for the forecast" : ""}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
