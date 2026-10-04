import { Fragment, useEffect, useMemo, useState } from "react";
import api from "../api";
import Icon from "../components/Icon.jsx";

export default function ManageUsers() {
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [resetFor, setResetFor] = useState(null);
  const [pw, setPw] = useState({ a: "", b: "" });
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  function load() {
    api
      .get("/admin/users")
      .then((r) => setUsers(r.data))
      .catch(() => {});
  }
  useEffect(load, []);

  const shown = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s
      ? users.filter((u) =>
          [u.username, u.full_name, u.email, u.role].some((v) =>
            v?.toLowerCase().includes(s),
          ),
        )
      : users;
  }, [users, q]);

  function openReset(u) {
    setResetFor(resetFor === u.user_id ? null : u.user_id);
    setPw({ a: "", b: "" });
    setMessage(null);
  }

  async function submitReset(e, u) {
    e.preventDefault();
    if (pw.a.length < 6)
      return setMessage({ type: "error", text: "Use at least 6 characters." });
    if (pw.a !== pw.b)
      return setMessage({
        type: "error",
        text: "The two passwords don't match.",
      });
    setBusy(true);
    try {
      const r = await api.post(`/admin/users/${u.user_id}/reset-password`, {
        new_password: pw.a,
      });
      setMessage({
        type: "success",
        text: `${r.data.message} Let them know the new one.`,
      });
      setResetFor(null);
      load();
    } catch (err) {
      setMessage({
        type: "error",
        text:
          err.response?.data?.detail?.[0]?.msg ||
          err.response?.data?.detail ||
          "Reset failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container">
      <div className="page-head">
        <div>
          <div className="eyebrow">Users</div>
          <h1 className="page-title">Registered users</h1>
          <p className="page-sub">
            Passwords are stored as bcrypt hashes and can't be read back, even
            by an admin. If someone is locked out, set a new one with Reset
            password.
          </p>
        </div>
      </div>

      {message && (
        <div className={`msg ${message.type}`}>
          <Icon name={message.type === "error" ? "alert" : "check"} />
          {message.text}
        </div>
      )}

      <section className="card flush">
        <div className="card-head">
          <h3>{users.length} accounts</h3>
          <div style={{ position: "relative", width: 260 }}>
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
              htmlFor="user-q"
              style={{
                position: "absolute",
                width: 1,
                height: 1,
                overflow: "hidden",
                clip: "rect(0 0 0 0)",
              }}
            >
              Search users
            </label>
            <input
              id="user-q"
              placeholder="Search name, email or role"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              style={{ paddingLeft: 30 }}
            />
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Password</th>
                <th>Registered</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {shown.map((u) => (
                <Fragment key={u.user_id}>
                  <tr className={resetFor === u.user_id ? "selected" : ""}>
                    <td className="mono">{u.user_id}</td>
                    <td style={{ fontWeight: 500 }}>
                      {u.full_name || <span className="muted">-</span>}
                    </td>
                    <td>{u.username}</td>
                    <td>
                      {u.email}
                      {!u.is_verified && (
                        <span
                          className="badge moderate"
                          style={{ marginLeft: 6 }}
                        >
                          Unverified
                        </span>
                      )}
                    </td>
                    <td>
                      <span
                        className={`badge ${u.role === "admin" ? "brand" : "neutral"}`}
                      >
                        {u.role === "admin" ? "Admin" : "Passenger"}
                      </span>
                    </td>
                    <td
                      className="mono muted"
                      title={u.password}
                      style={{ fontSize: 12 }}
                    >
                      {u.password ? `${u.password.slice(0, 12)}…` : "-"}{" "}
                      <span style={{ fontFamily: "var(--font-body)" }}>
                        (hashed)
                      </span>
                    </td>
                    <td className="mono">
                      {new Date(u.registration_time).toLocaleDateString([], {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </td>
                    <td className="r">
                      <button
                        className="btn small"
                        onClick={() => openReset(u)}
                        aria-expanded={resetFor === u.user_id}
                      >
                        Reset password
                      </button>
                    </td>
                  </tr>
                  {resetFor === u.user_id && (
                    <tr className="expand-row">
                      <td colSpan="8" style={{ padding: "4px 16px 16px" }}>
                        <form
                          className="reset-form"
                          onSubmit={(e) => submitReset(e, u)}
                        >
                          <div className="form-row">
                            <label htmlFor={`pw-a-${u.user_id}`}>
                              New password for {u.username}
                            </label>
                            <input
                              id={`pw-a-${u.user_id}`}
                              type="password"
                              autoComplete="new-password"
                              value={pw.a}
                              onChange={(e) =>
                                setPw((p) => ({ ...p, a: e.target.value }))
                              }
                              required
                            />
                          </div>
                          <div className="form-row">
                            <label htmlFor={`pw-b-${u.user_id}`}>
                              Type it again
                            </label>
                            <input
                              id={`pw-b-${u.user_id}`}
                              type="password"
                              autoComplete="new-password"
                              value={pw.b}
                              onChange={(e) =>
                                setPw((p) => ({ ...p, b: e.target.value }))
                              }
                              required
                            />
                          </div>
                          <button className="btn accent" disabled={busy}>
                            {busy ? "Saving…" : "Set password"}
                          </button>
                          <button
                            type="button"
                            className="btn ghost"
                            onClick={() => setResetFor(null)}
                          >
                            Cancel
                          </button>
                        </form>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {shown.length === 0 && (
                <tr className="empty-row">
                  <td colSpan="8">
                    {users.length
                      ? "No users match your search."
                      : "No users yet."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
