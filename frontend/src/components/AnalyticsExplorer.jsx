import { useEffect, useState } from "react";
import { api } from "../api";

const COLUMNS = [
  { key: "player_name", label: "Player", sortable: true, align: "left" },
  { key: "season", label: "Season", sortable: true, align: "right" },
  { key: "team_id", label: "Team", sortable: false, align: "left" },
  { key: "innings_pitched", label: "IP", sortable: true, align: "right" },
  { key: "so", label: "SO", sortable: true, align: "right" },
  { key: "bb", label: "BB", sortable: true, align: "right" },
  { key: "hr", label: "HR", sortable: true, align: "right" },
  { key: "era", label: "ERA", sortable: true, align: "right" },
  { key: "fip", label: "FIP", sortable: true, align: "right", premium: true },
];

const PAGE_SIZE = 25;

export default function AnalyticsExplorer() {
  const [seasons, setSeasons] = useState([]);
  const [search, setSearch] = useState("");
  const [season, setSeason] = useState("");
  const [minIp, setMinIp] = useState(50);
  const [sortBy, setSortBy] = useState("fip");
  const [order, setOrder] = useState("asc");
  const [page, setPage] = useState(1);

  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.seasons().then(setSeasons).catch(() => {});
  }, []);

  async function fetchData() {
    setLoading(true);
    setError("");
    try {
      const res = await api.pitching({
        search,
        season,
        min_ip: minIp,
        sort_by: sortBy,
        order,
        page,
        page_size: PAGE_SIZE,
      });
      setData(res);
    } catch (err) {
      setError(err.message);
      setData({ items: [], total: 0 });
    } finally {
      setLoading(false);
    }
  }

  // Refetch whenever a query input changes.
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [season, minIp, sortBy, order, page]);

  function onSearchSubmit(e) {
    e.preventDefault();
    setPage(1);
    fetchData();
  }

  function toggleSort(col) {
    if (!col.sortable) return;
    if (sortBy === col.key) {
      setOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(col.key);
      setOrder(col.key === "player_name" || col.key === "team_id" ? "asc" : "desc");
    }
    setPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="panel">
      <h2>Analytics Explorer</h2>
      <p className="subhead">
        Advanced pitching metrics computed from the Lahman database. FIP is a premium,
        metered stat.
      </p>

      <form className="filters" onSubmit={onSearchSubmit}>
        <input
          className="filter-search"
          placeholder="Search player name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={season} onChange={(e) => { setSeason(e.target.value); setPage(1); }}>
          <option value="">All seasons</option>
          {seasons.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <label className="ip-filter">
          Min IP
          <input
            type="number"
            min="0"
            value={minIp}
            onChange={(e) => { setMinIp(Number(e.target.value)); setPage(1); }}
          />
        </label>
        <button className="btn-primary" type="submit">Search</button>
      </form>

      {error && <div className="error-box">{error}</div>}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  className={`${c.align === "right" ? "ta-right" : ""} ${c.sortable ? "sortable" : ""}`}
                  onClick={() => toggleSort(c)}
                >
                  {c.label}
                  {c.premium && <span className="premium-tag">PRO</span>}
                  {sortBy === c.key && <span className="sort-arrow">{order === "asc" ? " ▲" : " ▼"}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={COLUMNS.length} className="empty">Loading…</td></tr>
            ) : data.items.length === 0 ? (
              <tr><td colSpan={COLUMNS.length} className="empty">No results.</td></tr>
            ) : (
              data.items.map((row) => (
                <tr key={`${row.player_id}-${row.season}-${row.team_id}`}>
                  <td>{row.player_name}</td>
                  <td className="ta-right">{row.season}</td>
                  <td>{row.team_id}</td>
                  <td className="ta-right">{row.innings_pitched}</td>
                  <td className="ta-right">{row.so}</td>
                  <td className="ta-right">{row.bb}</td>
                  <td className="ta-right">{row.hr}</td>
                  <td className="ta-right">{row.era}</td>
                  <td className="ta-right fip-cell">{row.fip}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <span>{data.total.toLocaleString()} rows</span>
        <div className="pager-controls">
          <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            ‹ Prev
          </button>
          <span className="page-indicator">Page {page} / {totalPages}</span>
          <button className="btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next ›
          </button>
        </div>
      </div>
    </div>
  );
}
