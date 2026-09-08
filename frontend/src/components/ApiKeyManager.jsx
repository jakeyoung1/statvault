import { useEffect, useState } from "react";
import { api, auth } from "../api";

export default function ApiKeyManager() {
  const [keyInfo, setKeyInfo] = useState(null);
  const [usage, setUsage] = useState(null);
  const [reveal, setReveal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const [k, u] = await Promise.all([api.getKeyInfo(), api.usage()]);
      setKeyInfo(k);
      setUsage(u);
      auth.setKey(k.key);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function regenerate() {
    if (!confirm("Regenerate API key? Your old key stops working immediately.")) return;
    setBusy(true);
    setError("");
    try {
      const k = await api.regenerateKey();
      auth.setKey(k.key);
      setKeyInfo(k);
      setReveal(true);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function copyKey() {
    if (!keyInfo) return;
    navigator.clipboard.writeText(keyInfo.key);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const pct = usage
    ? Math.min(100, Math.round((usage.requests_used / usage.monthly_limit) * 100))
    : 0;
  const meterClass = pct >= 90 ? "meter-danger" : pct >= 70 ? "meter-warn" : "meter-ok";
  const masked = keyInfo
    ? keyInfo.key.slice(0, 10) + "•".repeat(18) + keyInfo.key.slice(-4)
    : "";

  return (
    <div className="panel">
      <h2>API Key Manager</h2>
      {error && <div className="error-box">{error}</div>}

      <section className="card">
        <div className="card-head">
          <h3>Active API Key</h3>
          {keyInfo && (
            <span className={`status-dot ${keyInfo.active ? "on" : "off"}`}>
              {keyInfo.active ? "active" : "revoked"}
            </span>
          )}
        </div>
        <div className="key-row">
          <code className="key-value">{reveal ? keyInfo?.key : masked}</code>
          <button className="btn-ghost" onClick={() => setReveal((r) => !r)}>
            {reveal ? "Hide" : "Reveal"}
          </button>
          <button className="btn-ghost" onClick={copyKey}>
            {copied ? "Copied ✓" : "Copy"}
          </button>
        </div>
        <button className="btn-primary" onClick={regenerate} disabled={busy}>
          {busy ? "Regenerating…" : "Regenerate Key"}
        </button>
        <p className="hint">
          Send this key in the <code>X-API-Key</code> header on every request.
        </p>
      </section>

      <section className="card">
        <div className="card-head">
          <h3>Monthly Usage</h3>
          {usage && <span className="plan-badge">{usage.plan}</span>}
        </div>
        {usage && (
          <>
            <div className="meter">
              <div className={`meter-fill ${meterClass}`} style={{ width: `${pct}%` }} />
            </div>
            <div className="meter-stats">
              <span>
                <strong>{usage.requests_used.toLocaleString()}</strong> /{" "}
                {usage.monthly_limit.toLocaleString()} requests
              </span>
              <span>{usage.remaining.toLocaleString()} remaining</span>
            </div>
            <p className="hint">Period started {usage.period_start}. Resets monthly.</p>
          </>
        )}
      </section>
    </div>
  );
}
