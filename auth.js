const $ = (id) => document.getElementById(id);
const state = { user: null, mode: "login", busy: false };
const button = $("authButton"), modal = $("authModal"), form = $("authForm");
const status = $("authStatus"), submit = $("authSubmit");

function presetStorageKey() { return state.user ? `forge100k:user:${state.user.id}` : "forge100k:guest"; }
window.ForgeAuth = { storageKey: presetStorageKey };
if (!localStorage.getItem("forge100k:guest") && localStorage.getItem("forge100k")) localStorage.setItem("forge100k:guest", localStorage.getItem("forge100k"));

function message(text, error = false) { status.textContent = text; status.dataset.error = error ? "true" : "false"; }
function setBusy(value) {
  state.busy = value; submit.disabled = value;
  submit.textContent = value ? "Please wait…" : (state.mode === "signup" ? "Create account" : state.mode === "reset" ? "Password help" : "Sign in");
}
function showModal(mode = "login") {
  state.mode = mode;
  $("authTitle").textContent = mode === "signup" ? "Create your Forge account" : mode === "reset" ? "Local password help" : "Welcome back";
  $("authNameField").hidden = mode !== "signup";
  $("authEmailField").hidden = false; $("authEmail").required = true;
  $("authConfirmField").hidden = mode !== "signup";
  $("authModeLinks").hidden = mode === "reset";
  $("authSignupLink").hidden = mode === "signup"; $("authLoginLink").hidden = mode !== "signup";
  $("authResetLink").hidden = mode === "signup";
  $("authPasswordField").hidden = mode === "reset";
  $("authConfirm").required = mode === "signup";
  $("authPassword").required = mode !== "reset";
  $("authPassword").minLength = mode === "signup" ? 12 : 1;
  $("authConfirm").minLength = mode === "signup" ? 12 : 1;
  $("authPassword").autocomplete = mode === "signup" ? "new-password" : "current-password";
  setBusy(false);
  message(mode === "reset" ? "Password reset is local-only. Use the local admin reset command on the host; no email is sent." : "");
  modal.hidden = false; $("authEmail").focus();
}
function closeModal() { modal.hidden = true; form.reset(); message(""); }
function renderSession() {
  button.textContent = state.user ? "Account · " + (state.user.email || "Signed in") : "Sign in";
  button.setAttribute("aria-label", state.user ? "Sign out of Forge 100K" : "Sign in or create a Forge 100K account");
  window.dispatchEvent(new CustomEvent("forge:session-changed"));
}
async function api(path, payload) {
  const response = await fetch(path, {
    method: payload === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers: payload === undefined ? {} : { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload)
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error === "invalid_credentials" ? "Email or password is incorrect." : data.error || "Local server request failed.");
  return data;
}
async function restorePresets() {
  if (!state.user) return;
  const { presets } = await api("/api/presets");
  const local = JSON.parse(localStorage.getItem(presetStorageKey()) || "[]");
  const byId = new Map(local.map(x => [String(x.id), x]));
  for (const row of presets || []) byId.set(String(row.id), {
    id: row.id, name: row.name, style: row.config?.style || "Normal",
    body: row.config?.body || "Balanced", palette: row.config?.palette || "#b8f36b"
  });
  localStorage.setItem(presetStorageKey(), JSON.stringify([...byId.values()].slice(0, 100)));
  window.dispatchEvent(new CustomEvent("forge:session-changed"));
}
async function init() {
  try { const { user } = await api("/api/auth/session"); state.user = user || null; if (state.user) await restorePresets(); }
  catch (e) { console.error("Local Forge server unavailable:", e); }
  renderSession();
}
button.addEventListener("click", async () => {
  if (!state.user) return showModal("login");
  if (!confirm("Sign out of Forge 100K?")) return;
  try { await api("/api/auth/logout", {}); state.user = null; renderSession(); }
  catch (e) { message(e.message, true); }
});
$("authClose").addEventListener("click", closeModal);
modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });
$("authSignupLink").addEventListener("click", e => { e.preventDefault(); showModal("signup"); });
$("authLoginLink").addEventListener("click", e => { e.preventDefault(); showModal("login"); });
$("authResetLink").addEventListener("click", e => { e.preventDefault(); showModal("reset"); });
form.addEventListener("submit", async e => {
  e.preventDefault(); if (state.busy) return;
  if (state.mode === "reset") return message("No email service is used in local mode. Reset the password from the host machine using the documented local admin command.", true);
  const email = $("authEmail").value.trim().toLowerCase(), password = $("authPassword").value;
  setBusy(true);
  try {
    if (state.mode === "signup") {
      if (password.length < 12) throw new Error("Use a password with at least 12 characters.");
      if (password !== $("authConfirm").value) throw new Error("Passwords do not match.");
      const result = await api("/api/auth/signup", { email, password, name: $("authName").value.trim() });
      state.user = result.user;
    } else {
      const result = await api("/api/auth/login", { email, password });
      state.user = result.user;
    }
    await restorePresets(); closeModal();
  } catch (err) { message(err.message || "Authentication failed.", true); }
  finally { setBusy(false); renderSession(); }
});
window.addEventListener("forge:preset-saved", async e => {
  if (!state.user || !e.detail) return;
  const p = e.detail;
  try { await api("/api/presets", { id: String(p.id), name: String(p.name || "Untitled").slice(0,120), config: { style:p.style, body:p.body, palette:p.palette } }); }
  catch (err) { console.error("Local preset save failed:", err.message); }
});
init();
