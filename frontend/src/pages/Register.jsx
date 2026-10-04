import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    full_name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await register(form);

      navigate("/verify", {
        state: { email: res.data.email, devOtp: res.data.dev_otp },
      });
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="auth-brand">
          <img src="/logo.png" alt="" />
          <b>RailSky</b>
        </div>
        <h2>Create account</h2>
        <p className="sub">
          Create a passenger account to search trains and save trips
        </p>

        {error && <div className="msg error">{error}</div>}

        <div className="form-row">
          <label htmlFor="r-name">Full name</label>
          <input
            id="r-name"
            autoComplete="name"
            value={form.full_name}
            onChange={(e) => update("full_name", e.target.value)}
            required
          />
        </div>
        <div className="form-row">
          <label>Username</label>
          <input
            value={form.username}
            onChange={(e) => update("username", e.target.value)}
            required
          />
        </div>
        <div className="form-row">
          <label>Email</label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            required
          />
        </div>
        <div className="form-row">
          <label>Password</label>
          <input
            type="password"
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            required
          />
        </div>
        <button className="btn accent block" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>

        <div className="switch">
          Already registered? <Link to="/login">Sign in</Link>
        </div>
      </form>
    </div>
  );
}
