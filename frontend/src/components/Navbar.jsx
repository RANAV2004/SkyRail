import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import Icon from "./Icon.jsx";

function readTheme() {
  try {
    return localStorage.getItem("theme") || "light";
  } catch {
    return "light";
  }
}

const ADMIN_LINKS = [
  { to: "/admin", label: "Overview", icon: "home", end: true },
  { to: "/admin/optimizer", label: "Route planner", icon: "route" },
  { to: "/admin/weather", label: "Station weather", icon: "cloud" },
  { to: "/admin/model", label: "Delay model", icon: "clock" },
  { to: "/admin/users", label: "Users", icon: "users" },
];

const USER_LINKS = [
  { to: "/", label: "Overview", icon: "home", end: true },
  { to: "/find", label: "Find trains", icon: "search" },
  { to: "/tickets", label: "My trips", icon: "ticket" },
  { to: "/trains", label: "Timetable", icon: "train" },
];

// becomes a top bar on phones
export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [theme, setTheme] = useState(readTheme);
  const isAdmin = user?.role === "admin";
  const links = isAdmin ? ADMIN_LINKS : USER_LINKS;

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("theme", next);
    } catch {
      /* storage unavailable: theme still applies for this visit */
    }
  }

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside className="sidebar">
      <NavLink to={isAdmin ? "/admin" : "/"} className="brand">
        <img src="/logo.png" alt="" />
        <span>
          <b>RailSky</b>
          <small>{isAdmin ? "" : "Passenger"}</small>
        </span>
      </NavLink>
      <div className="section">{isAdmin ? "Operations" : "Travel"}</div>
      <nav>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end}>
            <Icon name={l.icon} />
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="foot">
        <div className="who">
          <span className="avatar">{user?.username?.[0] || "?"}</span>
          <span>{user?.username}</span>
        </div>
        <div className="row">
          <button
            className="btn small icon-only"
            onClick={toggleTheme}
            title={
              theme === "dark"
                ? "Switch to light theme"
                : "Switch to dark theme"
            }
            aria-label={
              theme === "dark"
                ? "Switch to light theme"
                : "Switch to dark theme"
            }
          >
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          <button className="btn small" onClick={handleLogout}>
            <Icon name="logout" size={14} /> Log out
          </button>
        </div>
      </div>
    </aside>
  );
}
