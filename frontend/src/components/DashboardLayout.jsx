import { useState } from "react";
import ApiKeyManager from "./ApiKeyManager.jsx";
import AnalyticsExplorer from "./AnalyticsExplorer.jsx";
import Documentation from "./Documentation.jsx";

const TABS = [
  { id: "keys", label: "API Key Manager" },
  { id: "analytics", label: "Analytics Explorer" },
  { id: "docs", label: "Documentation" },
];

export default function DashboardLayout({ user, onLogout }) {
  const [tab, setTab] = useState("analytics");

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">⬢</span>
          <span className="brand-name">StatVault</span>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? "tab-active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="user-box">
          <span className={`plan-badge plan-${user.plan}`}>{user.plan}</span>
          <span className="user-email">{user.email}</span>
          <button className="btn-ghost" onClick={onLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="content">
        {tab === "keys" && <ApiKeyManager />}
        {tab === "analytics" && <AnalyticsExplorer />}
        {tab === "docs" && <Documentation />}
      </main>
    </div>
  );
}
