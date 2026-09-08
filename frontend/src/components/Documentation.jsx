import { useEffect, useState } from "react";
import { api, auth } from "../api";

const LANGS = ["cURL", "Python", "JavaScript"];

function snippets(base, key) {
  const url = `${base}/api/v1/metrics/pitching`;
  return {
    cURL: `curl "${url}?season=2019&min_ip=150&sort_by=fip&order=asc" \\
  -H "X-API-Key: ${key}"`,
    Python: `import requests

resp = requests.get(
    "${url}",
    headers={"X-API-Key": "${key}"},
    params={"season": 2019, "min_ip": 150, "sort_by": "fip", "order": "asc"},
)
resp.raise_for_status()
for row in resp.json()["items"]:
    print(row["player_name"], row["era"], row["fip"])`,
    JavaScript: `const res = await fetch(
  "${url}?season=2019&min_ip=150&sort_by=fip&order=asc",
  { headers: { "X-API-Key": "${key}" } }
);
const data = await res.json();
console.table(data.items);`,
  };
}

export default function Documentation() {
  const [lang, setLang] = useState("cURL");
  const [key, setKey] = useState(auth.getKey() || "YOUR_API_KEY");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.getKeyInfo().then((k) => setKey(k.key)).catch(() => {});
  }, []);

  const code = snippets(api.base, key)[lang];

  function copy() {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="panel">
      <h2>Documentation</h2>
      <p className="subhead">Query the StatVault API with your key. Examples are pre-filled with your live key.</p>

      <section className="card">
        <h3>Endpoint</h3>
        <code className="endpoint">GET {api.base}/api/v1/metrics/pitching</code>
        <table className="params-table">
          <thead><tr><th>Param</th><th>Type</th><th>Description</th></tr></thead>
          <tbody>
            <tr><td>search</td><td>string</td><td>Filter by player name (substring)</td></tr>
            <tr><td>season</td><td>int</td><td>Filter by season, e.g. 2019</td></tr>
            <tr><td>team</td><td>string</td><td>Team code, e.g. BOS</td></tr>
            <tr><td>min_ip</td><td>float</td><td>Minimum innings pitched</td></tr>
            <tr><td>sort_by</td><td>string</td><td>era · fip · so · bb · hr · season · innings_pitched</td></tr>
            <tr><td>order</td><td>string</td><td>asc · desc</td></tr>
            <tr><td>page / page_size</td><td>int</td><td>Pagination (max page_size 100)</td></tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="card-head">
          <h3>Code Examples</h3>
          <div className="lang-tabs">
            {LANGS.map((l) => (
              <button
                key={l}
                className={`lang-tab ${lang === l ? "lang-active" : ""}`}
                onClick={() => setLang(l)}
              >
                {l}
              </button>
            ))}
          </div>
        </div>
        <div className="code-block">
          <button className="copy-btn" onClick={copy}>{copied ? "Copied ✓" : "Copy"}</button>
          <pre>{code}</pre>
        </div>
      </section>

      <section className="card">
        <h3>Authentication</h3>
        <p className="hint">
          Every request must include your secret key in the <code>X-API-Key</code> header.
          Premium stats (FIP) count against your monthly quota; requests over the limit
          return <code>429 Too Many Requests</code>. Missing or invalid keys return
          <code> 401 Unauthorized</code>.
        </p>
      </section>
    </div>
  );
}
