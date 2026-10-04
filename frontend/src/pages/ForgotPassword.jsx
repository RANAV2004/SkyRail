import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api";

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [devOtp, setDevOtp] = useState(null);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);

  async function requestOtp(e) {
    e.preventDefault();
    setMessage(null);
    setBusy(true);
    try {
      const res = await api.post("/auth/forgot-password", { email });
      setDevOtp(res.data.dev_otp || null);
      setStep(2);
      setMessage({
        type: "success",
        text: res.data.email_sent
          ? "OTP sent to your email."
          : "OTP generated (dev mode).",
      });
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Could not send OTP",
      });
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(e) {
    e.preventDefault();
    setMessage(null);
    setBusy(true);
    try {
      await api.post("/auth/reset-password", {
        email,
        otp,
        new_password: newPassword,
      });
      setMessage({
        type: "success",
        text: "Password reset! Redirecting to login…",
      });
      setTimeout(() => navigate("/login"), 1000);
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "Reset failed",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <form
        className="auth-card"
        onSubmit={step === 1 ? requestOtp : resetPassword}
      >
        <div className="auth-brand">
          <img src="/logo.png" alt="" />
          <b>RailSky</b>
        </div>
        <h2>Reset password</h2>
        <p className="sub">
          {step === 1
            ? "Enter your account email to receive a reset code."
            : "Enter the code and choose a new password."}
        </p>

        {message && <div className={`msg ${message.type}`}>{message.text}</div>}

        {devOtp && step === 2 && (
          <div
            className="msg success"
            style={{ fontFamily: "var(--font-mono)", flexDirection: "column" }}
          >
            Dev mode, your OTP is <strong>{devOtp}</strong>
          </div>
        )}

        <div className="form-row">
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={step === 2}
            required
          />
        </div>

        {step === 2 && (
          <>
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
            <div className="form-row">
              <label>New password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>
          </>
        )}

        <button className="btn accent block" disabled={busy}>
          {busy
            ? "Please wait…"
            : step === 1
              ? "Send reset code"
              : "Reset password"}
        </button>

        {step === 2 && (
          <div className="switch">
            <button
              type="button"
              className="btn ghost small"
              onClick={() => setStep(1)}
            >
              ← Use a different email
            </button>
          </div>
        )}
        <div className="switch">
          <Link to="/login">Back to login</Link>
        </div>
      </form>
    </div>
  );
}
