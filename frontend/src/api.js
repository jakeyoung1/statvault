// Thin StatVault API client. The API key is the session token.
const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8010";

const KEY_STORE = "statvault_api_key";
const USER_STORE = "statvault_user";

export const auth = {
  getKey: () => localStorage.getItem(KEY_STORE),
  getUser: () => JSON.parse(localStorage.getItem(USER_STORE) || "null"),
  setSession: (key, user) => {
    localStorage.setItem(KEY_STORE, key);
    localStorage.setItem(USER_STORE, JSON.stringify(user));
  },
  setKey: (key) => localStorage.setItem(KEY_STORE, key),
  clear: () => {
    localStorage.removeItem(KEY_STORE);
    localStorage.removeItem(USER_STORE);
  },
};

async function request(path, { method = "GET", body, withKey = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (withKey) {
    const key = auth.getKey();
    if (key) headers["X-API-Key"] = key;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  base: API_BASE,
  login: (email, password) =>
    request("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
      withKey: false,
    }),
  me: () => request("/api/v1/account/me"),
  getKeyInfo: () => request("/api/v1/account/key"),
  regenerateKey: () =>
    request("/api/v1/account/key/regenerate", { method: "POST" }),
  usage: () => request("/api/v1/account/usage"),
  seasons: () => request("/api/v1/metrics/seasons"),
  pitching: (params) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== "" && v != null)
    ).toString();
    return request(`/api/v1/metrics/pitching?${qs}`);
  },
};
