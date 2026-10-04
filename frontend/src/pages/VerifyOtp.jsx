import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import api from "../api";

export default function VerifyOtp() {
  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = useState(location.state?.email || "");
  const [otp, setOtp] = useState("");
  const [devOtp, setDevOtp] = useState(location.state?.devOtp || null);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleVerify(e) {
    e.preventDefault();
    setMessage(null);
    setBusy(true);
    try {
      await api.post("/auth/verify-otp", { email, otp });
      setMessage({
        type: "success",
        text: "Email verified! Redirecting to login…",
      });
      setTimeout(() => navigate("/login"), 1000);
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Verification failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    setMessage(null);
    try {
      const res = await api.post("/auth/resend-otp", { email });
      setDevOtp(res.data.dev_otp || null);
      setMessage({
        type: "success",
        text: res.data.email_sent
          ? "A new OTP has been sent to your email."
          : "A new OTP was generated (dev mode).",
      });
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Could not resend OTP",
      });
    }
  }

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={handleVerify}>
        <div className="auth-brand">
          <img src="/logo.png" alt="" />
          <b>RailSky</b>
        </div>
        <h2>Verify your email</h2>
        <p className="sub">
          Enter the 6-digit code we sent to your email address.
        </p>

        {message && <div className={`msg ${message.type}`}>{message.text}</div>}

        {devOtp && (
          <div
            className="msg success"
            style={{ fontFamily: "var(--font-mono)", flexDirection: "column" }}
          >
            Dev mode, your OTP is <strong>{devOtp}</strong>
            <div style={{ fontSize: 12, marginTop: 4, color: "var(--ok)" }}>
              (Shown because email/SMTP isn't configured. It's also printed in
              the server console.)
            </div>
          </div>
        )}

        <div className="form-row">
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="form-row">
          <label>OTP</label>
          <input
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            maxLength={6}
            placeholder="6-digit code"
            style={{ letterSpacing: 4, fontSize: 18, textAlign: "center" }}
            required
          />
        </div>
        <button className="btn accent block" disabled={busy}>
          {busy ? "Verifying…" : "Verify"}
        </button>

        <div className="switch">
          Didn't get it?{" "}
          <button
            type="button"
            className="btn ghost small"
            onClick={handleResend}
            style={{ marginLeft: 6 }}
          >
            Resend OTP
          </button>
        </div>
        <div className="switch">
          <Link to="/login">Back to login</Link>
        </div>
      </form>
    </div>
  );
}
