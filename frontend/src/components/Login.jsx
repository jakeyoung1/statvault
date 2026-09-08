import { useState } from "react";
import { api, auth } from "../api";

const DEMO = [
  { email: "pro@statvault.io", password: "pro12345", note: "Pro · 50k/mo" },
  { email: "demo@statvault.io", password: "demo1234", note: "Free · 1k/mo" },
  { email: "trial@statvault.io", password: "trial123", note: "Trial · 5/mo" },
];

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { user, api_key } = await api.login(email, password);
      auth.setSession(api_key, user);
      onLogin(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(d) {
    setEmail(d.email);
    setPassword(d.password);
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="brand">
          <span className="brand-mark">⬢</span>
          <span className="brand-name">StatVault</span>
        </div>
        <p className="auth-sub">Developer Portal · MLB Advanced Metrics API</p>

        <form onSubmit={submit}>
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
          {error && <div className="error-box">{error}</div>}
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <div className="demo-creds">
          <span className="demo-label">Demo accounts — click to fill</span>
          {DEMO.map((d) => (
            <button key={d.email} className="demo-chip" onClick={() => fillDemo(d)}>
              <strong>{d.email}</strong>
              <span>{d.note}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
