import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [needsVerify, setNeedsVerify] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setNeedsVerify(false);
    setBusy(true);
    try {
      const data = await login(username, password);
      navigate(data.role === "admin" ? "/admin" : "/");
    } catch (err) {
      if (err.response?.status === 403) setNeedsVerify(true);
      setError(err.response?.data?.detail || "Login failed");
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
        <h2>Sign in</h2>

        {error && <div className="msg error">{error}</div>}
        {needsVerify && (
          <div className="msg success" style={{ marginTop: -6 }}>
            <Link to="/verify">Verify your email now</Link>
          </div>
        )}

        <div className="form-row">
          <label>Username </label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div className="form-row">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button className="btn accent block" disabled={busy}>
          {busy ? (
            <>
              <span className="spinner" /> Signing in…
            </>
          ) : (
            "Sign in"
          )}
        </button>

        <div className="switch">
          <Link to="/forgot">Forgot password?</Link>
        </div>
        <div className="switch">
          New here? <Link to="/register">Create an account</Link>
        </div>
      </form>
    </div>
  );
}
