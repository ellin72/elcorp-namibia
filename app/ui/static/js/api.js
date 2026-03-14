/* ===== Elcorp UI — API Client ===== */

const API = (() => {
  const BASE = "/api/v1";

  function getToken() {
    return localStorage.getItem("access_token");
  }
  function getRefresh() {
    return localStorage.getItem("refresh_token");
  }
  function setTokens(access, refresh) {
    localStorage.setItem("access_token", access);
    if (refresh) localStorage.setItem("refresh_token", refresh);
  }
  function clearTokens() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }
  function getUser() {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  }
  function setUser(u) {
    localStorage.setItem("user", JSON.stringify(u));
  }

  async function request(method, path, body, retry) {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    const opts = { method, headers };
    if (body && method !== "GET") opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    if (res.status === 401 && !retry) {
      const refreshed = await refreshToken();
      if (refreshed) return request(method, path, body, true);
      window.location.href = "/ui/login";
      return null;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { status: res.status, ...data };
    return data;
  }

  async function uploadFile(path, formData, retry) {
    const headers = {};
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(BASE + path, {
      method: "POST",
      headers,
      body: formData,
    });
    if (res.status === 401 && !retry) {
      const refreshed = await refreshToken();
      if (refreshed) return uploadFile(path, formData, true);
      window.location.href = "/ui/login";
      return null;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw { status: res.status, ...data };
    return data;
  }

  async function refreshToken() {
    const rt = getRefresh();
    if (!rt) return false;
    try {
      const res = await fetch(BASE + "/auth/refresh", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: rt }),
      });
      if (!res.ok) {
        clearTokens();
        return false;
      }
      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return true;
    } catch {
      clearTokens();
      return false;
    }
  }

  /* ------- Auth ------- */
  const auth = {
    async login(email, password) {
      const data = await request("POST", "/auth/login", { email, password });
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    },
    async signup(payload) {
      const data = await request("POST", "/auth/signup", payload);
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user);
      return data;
    },
    async logout() {
      try {
        await request("POST", "/auth/logout");
      } catch {}
      clearTokens();
    },
    async validate() {
      return request("GET", "/auth/validate");
    },
    isLoggedIn() {
      return !!getToken();
    },
    getUser,
    clearTokens,
    setUser,
  };

  /* ------- Identity ------- */
  const identity = {
    getMe: () => request("GET", "/me"),
    updateMe: (d) => request("PUT", "/me", d),
    getPermissions: () => request("GET", "/me/permissions"),
    getUser: (id) => request("GET", "/users/" + id),
    listUsers: () => request("GET", "/users"),
  };

  /* ------- KYC ------- */
  const kyc = {
    upload: (fd) => uploadFile("/kyc/upload", fd),
    list: () => request("GET", "/kyc/documents"),
    review: (id, d) => request("POST", "/kyc/" + id + "/review", d),
    pending: () => request("GET", "/kyc/pending"),
  };

  /* ------- Payments ------- */
  const payments = {
    create: (d) => request("POST", "/payments", d),
    list: () => request("GET", "/payments"),
    get: (id) => request("GET", "/payments/" + id),
    process: (id) => request("POST", "/payments/" + id + "/process"),
    createToken: (d) => request("POST", "/payments/tokens", d),
    simulatePayout: (d) => request("POST", "/payments/simulate-payout", d),
  };

  /* ------- Merchants ------- */
  const merchants = {
    create: (d) => request("POST", "/merchants", d),
    list: () => request("GET", "/merchants"),
    get: (id) => request("GET", "/merchants/" + id),
    update: (id, d) => request("PUT", "/merchants/" + id, d),
    deactivate: (id) => request("POST", "/merchants/" + id + "/deactivate"),
  };

  /* ------- Webhooks ------- */
  const webhooks = {
    create: (d) => request("POST", "/webhooks", d),
    list: (merchantId) => request("GET", "/webhooks/" + merchantId),
    remove: (id) => request("DELETE", "/webhooks/" + id),
  };

  /* ------- Admin ------- */
  const admin = {
    stats: () => request("GET", "/admin/stats"),
    auditLogs: () => request("GET", "/admin/audit-logs"),
    setRoles: (userId, roles) =>
      request("PUT", "/admin/users/" + userId + "/roles", { roles }),
    deactivateUser: (userId) =>
      request("POST", "/admin/users/" + userId + "/deactivate"),
  };

  /* ------- Health ------- */
  const health = {
    simple: () => fetch(BASE + "/health").then((r) => r.json()),
    ready: () => fetch(BASE + "/health/ready").then((r) => r.json()),
  };

  return {
    auth,
    identity,
    kyc,
    payments,
    merchants,
    webhooks,
    admin,
    health,
    getUser,
    setUser,
  };
})();

/* ===== UI Helpers ===== */

function showAlert(id, msg, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "alert alert-" + type + " show";
  el.textContent = msg;
  setTimeout(() => el.classList.remove("show"), 5000);
}

function initTabs(container) {
  const btns = container.querySelectorAll(".tab-btn");
  const panels = container.querySelectorAll(".tab-panel");
  btns.forEach((b) =>
    b.addEventListener("click", () => {
      btns.forEach((x) => x.classList.remove("active"));
      panels.forEach((x) => x.classList.remove("active"));
      b.classList.add("active");
      const target = container.querySelector("#" + b.dataset.tab);
      if (target) target.classList.add("active");
    }),
  );
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-ZA", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function badgeClass(status) {
  const s = (status || "").toLowerCase();
  if (["completed", "ok", "active", "verified", "approved"].includes(s))
    return "badge-ok";
  if (["pending", "configured", "submitted"].includes(s))
    return "badge-pending";
  if (["failed", "error", "suspended", "rejected"].includes(s))
    return "badge-failed";
  if (["processing"].includes(s)) return "badge-processing";
  return "badge-unavailable";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str || ""));
  return div.innerHTML;
}

/* Update nav auth state */
function updateNav() {
  const loggedIn = API.auth.isLoggedIn();
  document
    .querySelectorAll(".auth-only")
    .forEach((el) => (el.style.display = loggedIn ? "" : "none"));
  document
    .querySelectorAll(".guest-only")
    .forEach((el) => (el.style.display = loggedIn ? "none" : ""));
  const user = API.auth.getUser();
  const avatarEl = document.querySelector(".avatar");
  if (avatarEl && user)
    avatarEl.textContent = (user.first_name ||
      user.email ||
      "?")[0].toUpperCase();
  const nameEl = document.querySelector(".user-name");
  if (nameEl && user) nameEl.textContent = user.first_name || user.email || "";
}

document.addEventListener("DOMContentLoaded", updateNav);
