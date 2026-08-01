import { supabase, authAvailable } from "./auth.js";

const $ = (id) => document.getElementById(id);

function show(id) {
  ["adminLogin", "adminRecovery", "adminNewPassword", "adminDashboard"].forEach(
    (s) => $(s).classList.toggle("hidden", s !== id)
  );
}

function setMsg(id, text, ok = true) {
  const el = $(id);
  el.textContent = text;
  el.classList.remove("hidden");
  el.className = "admin-msg " + (ok ? "admin-msg--ok" : "admin-msg--err");
}

function clearMsg(id) {
  $(id).classList.add("hidden");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function apiCall(path, token, options = {}) {
  const res = await fetch(path, {
    method: options.method || "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    let detail = "Error " + res.status;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch { /* noop */ }
    throw new Error(detail);
  }
  return res.json();
}

function describeError(e) {
  const s = Number(e.status_code);
  const path = e.endpoint || "";
  if ((s === 401 || s === 403) && path.startsWith("/api/admin"))
    return "Acceso al panel sin permisos de administrador";
  if (s === 400 && path.includes("/api/clean"))
    return "La limpieza rechazó el archivo (datos inválidos)";
  if (s === 401) return "Sesión no autorizada / token inválido";
  if (s === 403) return "Acceso denegado";
  if (s === 404) return "Recurso no encontrado";
  if (s === 422) return "Validación de datos fallida";
  if (s >= 500) return "Error interno del servidor";
  if (s === 400) return "Petición inválida (datos mal formados)";
  return "Error HTTP " + s;
}

async function getTokenOrNull() {
  if (!supabase || !authAvailable) return null;
  try {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token || null;
  } catch {
    return null;
  }
}

function renderKpis(daily) {
  const wrap = $("adminKpis");
  const today = (daily && daily[0]) || {};
  const users = daily ? daily.reduce((a, d) => a + Number(d.active_users || 0), 0) : 0;
  const requests = daily ? daily.reduce((a, d) => a + Number(d.requests || 0), 0) : 0;
  const errors = daily ? daily.reduce((a, d) => a + Number(d.errors || 0), 0) : 0;
  const avgMs = today.avg_duration_ms ? Number(today.avg_duration_ms) : 0;
  wrap.innerHTML = [
    `<div class="kpi"><div class="kpi__value">${users}</div><div class="kpi__label">Usuarios activos (suma)</div></div>`,
    `<div class="kpi"><div class="kpi__value">${requests}</div><div class="kpi__label">Peticiones API</div></div>`,
    `<div class="kpi"><div class="kpi__value">${errors}</div><div class="kpi__label">Errores totales</div></div>`,
    `<div class="kpi"><div class="kpi__value">${avgMs ? (avgMs / 1000).toFixed(2) : 0}s</div><div class="kpi__label">Tiempo promedio por petición</div></div>`,
  ].join("");
}

function renderDaily(daily) {
  const wrap = $("adminDailyWrap");
  if (!daily || daily.length === 0) {
    wrap.innerHTML = `<p class="admin-note">Sin datos aún.</p>`;
    return;
  }
  const rows = daily
    .map(
      (d) => `<tr>
        <td>${d.day || "-"}</td>
        <td>${d.active_users ?? 0}</td>
        <td>${d.requests ?? 0}</td>
        <td>${d.avg_duration_ms ? (Number(d.avg_duration_ms) / 1000).toFixed(2) + "s" : "-"}</td>
        <td>${d.errors ? `<span class="badge-err">${d.errors}</span>` : `<span class="badge-ok">0</span>`}</td>
      </tr>`
    )
    .join("");
  wrap.innerHTML = `<table class="admin-table">
    <thead><tr><th>Día</th><th>Usuarios</th><th>Peticiones</th><th>Prom. duración</th><th>Errores</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function renderErrors(errors) {
  const wrap = $("adminErrorsWrap");
  const resolveBtn = $("adminResolveErrorsButton");
  if (!errors || errors.length === 0) {
    wrap.innerHTML = `<p class="admin-note">Sin errores pendientes.</p>`;
    if (resolveBtn) resolveBtn.style.display = "none";
    return;
  }
  if (resolveBtn) resolveBtn.style.display = "";

  const groups = new Map();
  for (const e of errors) {
    const key = `${e.endpoint}|${e.status_code}|${e.error_type}`;
    if (!groups.has(key)) {
      groups.set(key, { endpoint: e.endpoint, status_code: e.status_code, error_type: e.error_type, count: 0, last_seen: e.created_at || "" });
    }
    const g = groups.get(key);
    g.count += 1;
    if ((e.created_at || "") > (g.last_seen || "")) g.last_seen = e.created_at || "";
  }

  const rows = [...groups.values()]
    .map(
      (e) => `<tr>
        <td>${escapeHtml(describeError(e))}</td>
        <td><code>${escapeHtml(e.endpoint || "-")}</code></td>
        <td><span class="badge-err">${e.status_code}</span></td>
        <td>${escapeHtml(e.error_type || "-")}</td>
        <td>${e.count}${e.count > 1 ? " veces" : ""}</td>
        <td>${(e.last_seen || "-").slice(0, 19).replace("T", " ")}</td>
      </tr>`
    )
    .join("");
  wrap.innerHTML = `<table class="admin-table">
    <thead><tr><th>Descripción</th><th>Endpoint</th><th>Status</th><th>Tipo</th><th>Veces</th><th>Última vez</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function renderHistory(resolved) {
  const btn = $("adminToggleHistoryButton");
  const wrap = $("adminHistoryWrap");
  if (!resolved || resolved.length === 0) {
    if (btn) btn.style.display = "none";
    if (wrap) { wrap.classList.add("hidden"); wrap.innerHTML = ""; }
    return;
  }
  if (btn) {
    btn.style.display = "";
    btn.textContent = wrap.classList.contains("hidden") ? `Ver historial (${resolved.length})` : "Ocultar historial";
  }
  const rows = resolved
    .map(
      (e) => `<tr>
        <td><code>${escapeHtml(e.endpoint || "-")}</code></td>
        <td><span class="badge-err">${e.status_code}</span></td>
        <td>${escapeHtml(e.error_type || "-")}</td>
        <td>${(e.created_at || "-").slice(0, 19).replace("T", " ")}</td>
      </tr>`
    )
    .join("");
  if (wrap) wrap.innerHTML = `<table class="admin-table">
    <thead><tr><th>Endpoint</th><th>Status</th><th>Tipo</th><th>Fecha</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

async function loadDashboard(token) {
  clearMsg("adminDashMsg");
  try {
    const [metricsRes, errorsRes, resolvedRes] = await Promise.all([
      apiCall("/api/admin/metrics", token),
      apiCall("/api/admin/errors", token),
      apiCall("/api/admin/errors?resolved=true&limit=100", token),
    ]);
    const daily = metricsRes.metrics?.daily || [];
    renderKpis(daily);
    renderDaily(daily);
    renderErrors(errorsRes.errors || []);
    renderHistory(resolvedRes.errors || []);
  } catch (e) {
    setMsg("adminDashMsg", "No tienes permisos de administrador: " + e.message, false);
  }
}

function isRecoveryLink() {
  return /[?&#]type=recovery/.test(window.location.hash + window.location.search);
}

async function init() {
  if (!authAvailable) {
    const start = Date.now();
    while (!authAvailable && Date.now() - start < 6000) {
      await new Promise((r) => setTimeout(r, 120));
    }
  }
  const token = await getTokenOrNull();
  if (!supabase || !authAvailable) {
    setMsg("adminLoginMsg", "El servicio de autenticación no está disponible. Verifica tu conexión.", false);
    show("adminLogin");
    return;
  }

  // Llegada desde el enlace de recuperación de contraseña
  if (isRecoveryLink()) {
    show("adminNewPassword");
    return;
  }

  if (token) {
    await loadDashboard(token);
    show("adminDashboard");
  } else {
    show("adminLogin");
  }
}

function bindEvents() {
  supabase?.auth?.onAuthStateChange((event) => {
    if (event === "PASSWORD_RECOVERY") show("adminNewPassword");
  });

  $("adminGoogleButton").addEventListener("click", async () => {
    clearMsg("adminLoginMsg");
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: window.location.origin + "/admin", scopes: "openid email profile" },
      });
      if (error) setMsg("adminLoginMsg", error.message, false);
    } catch (e) {
      setMsg("adminLoginMsg", e.message, false);
    }
  });

  $("adminPasswordForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMsg("adminLoginMsg");
    const email = $("adminEmail").value.trim();
    const password = $("adminPassword").value;
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      const token = await getTokenOrNull();
      await loadDashboard(token);
      show("adminDashboard");
    } catch (err) {
      setMsg("adminLoginMsg", "Credenciales inválidas: " + err.message, false);
    }
  });

  $("adminForgotButton").addEventListener("click", () => show("adminRecovery"));
  $("adminBackLoginButton").addEventListener("click", () => show("adminLogin"));

  $("adminRecoveryForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = $("adminRecoveryEmail").value.trim();
    setMsg("adminRecoveryMsg", "Enviando enlace…", true);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: window.location.origin + "/admin",
      });
      if (error) throw error;
      setMsg("adminRecoveryMsg", "Revisa tu correo. Te enviamos un enlace seguro para restablecer la contraseña.", true);
    } catch (err) {
      setMsg("adminRecoveryMsg", err.message, false);
    }
  });

  $("adminNewPasswordForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const p1 = $("adminNewPassword").value;
    const p2 = $("adminNewPassword2").value;
    if (p1.length < 8) {
      setMsg("adminNewPasswordMsg", "La contraseña debe tener al menos 8 caracteres.", false);
      return;
    }
    if (p1 !== p2) {
      setMsg("adminNewPasswordMsg", "Las contraseñas no coinciden.", false);
      return;
    }
    try {
      const { error } = await supabase.auth.updateUser({ password: p1 });
      if (error) throw error;
      setMsg("adminNewPasswordMsg", "Contraseña actualizada. Ya puedes iniciar sesión.", true);
      setTimeout(() => show("adminLogin"), 1500);
    } catch (err) {
      setMsg("adminNewPasswordMsg", err.message, false);
    }
  });

  $("adminRefreshButton").addEventListener("click", async () => {
    const token = await getTokenOrNull();
    if (token) await loadDashboard(token);
  });

  $("adminResolveErrorsButton").addEventListener("click", async () => {
    const token = await getTokenOrNull();
    if (!token) return;
    setMsg("adminDashMsg", "Marcando errores como resueltos…", true);
    try {
      const data = await apiCall("/api/admin/errors/resolve", token, { method: "POST", body: {} });
      setMsg("adminDashMsg", `${data.resolved} error(es) marcado(s) como resuelto(s).`, true);
      await loadDashboard(token);
    } catch (e) {
      setMsg("adminDashMsg", e.message, false);
    }
  });

  $("adminToggleHistoryButton").addEventListener("click", () => {
    const wrap = $("adminHistoryWrap");
    const wasHidden = wrap.classList.contains("hidden");
    wrap.classList.toggle("hidden");
    $("adminToggleHistoryButton").textContent = wasHidden ? "Ocultar historial" : "Ver historial";
  });

  $("adminSendErrorsButton").addEventListener("click", async () => {
    const token = await getTokenOrNull();
    if (!token) return;
    setMsg("adminDashMsg", "Enviando reporte de errores…", true);
    try {
      const res = await fetch("/api/admin/errors/send", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail || "Error " + res.status);
      const status = body.result?.status;
      setMsg(
        "adminDashMsg",
        status === "sent"
          ? "Reporte de errores enviado por email correctamente."
          : status === "no_webhook"
          ? "Webhook de Make.com no configurado (MAKE_WEBHOOK_URL)."
          : "Fallo al enviar: " + JSON.stringify(body.result),
        status === "sent"
      );
    } catch (e) {
      setMsg("adminDashMsg", e.message, false);
    }
  });

  $("adminLogoutButton").addEventListener("click", async () => {
    await supabase.auth.signOut();
    show("adminLogin");
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => { bindEvents(); init(); });
} else {
  bindEvents();
  init();
}
