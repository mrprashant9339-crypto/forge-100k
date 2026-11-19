import { SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_CONFIGURED } from "./supabase-config.js";

const $ = (id) => document.getElementById(id);
const state = { client: null, user: null, mode: "login", busy: false };
const button = $("authButton");
const modal = $("authModal");
const form = $("authForm");
const status = $("authStatus");
const submit = $("authSubmit");

function presetStorageKey() {
  return state.user ? `forge100k:user:${state.user.id}` : "forge100k:guest";
}
window.ForgeAuth = { storageKey: presetStorageKey };

if (!localStorage.getItem("forge100k:guest") && localStorage.getItem("forge100k")) {
  localStorage.setItem("forge100k:guest", localStorage.getItem("forge100k"));
}

function message(text, error = false) {
  status.textContent = text;
  status.dataset.error = error ? "true" : "false";
}
function setBusy(value) {
  state.busy = value;
  submit.disabled = value;
  submit.textContent = value ? "Please wait…" : (state.mode === "signup" ? "Create account" : state.mode === "reset" ? "Send reset link" : state.mode === "recovery" ? "Update password" : "Sign in");
}
function showModal(mode = "login") {
  state.mode = mode;
  $("authTitle").textContent = mode === "signup" ? "Create your Forge account" : mode === "reset" ? "Reset password" : mode === "recovery" ? "Choose a new password" : "Welcome back";
  $("authNameField").hidden = mode !== "signup";
  $("authEmailField").hidden = mode === "recovery";
  $("authEmail").required = mode !== "recovery";
  $("authConfirmField").hidden = mode !== "signup" && mode !== "recovery";
  $("authModeLinks").hidden = mode === "reset" || mode === "recovery";
  $("authSignupLink").hidden = mode === "signup";
  $("authLoginLink").hidden = mode !== "signup";
  $("authResetLink").hidden = mode === "signup";
  $("authPasswordField").hidden = mode === "reset";
  $("authConfirm").required = mode === "signup" || mode === "recovery";
  $("authPassword").required = mode !== "reset";
  $("authPassword").minLength = mode === "signup" || mode === "recovery" ? 12 : 1;
  $("authConfirm").minLength = mode === "signup" || mode === "recovery" ? 12 : 1;
  $("authPassword").autocomplete = mode === "signup" || mode === "recovery" ? "new-password" : "current-password";
  setBusy(false);
  message(SUPABASE_CONFIGURED ? "" : "Authentication is not configured yet. Add your Supabase project URL and public key in supabase-config.js, then apply supabase/schema.sql.");
  modal.hidden = false;
  $("authEmail").focus();
}
function closeModal() { modal.hidden = true; form.reset(); message(""); }
function renderSession() {
  if (state.user) {
    button.textContent = "Account · " + (state.user.email || "Signed in");
    button.setAttribute("aria-label", "Sign out of Forge 100K");
  } else {
    button.textContent = "Sign in";
    button.setAttribute("aria-label", "Sign in or create a Forge 100K account");
  }
  window.dispatchEvent(new CustomEvent("forge:session-changed"));
}
async function syncPreset(preset) {
  if (!state.client || !state.user || !preset) return;
  const { error } = await state.client.from("saved_presets").upsert({
    user_id: state.user.id,
    preset_id: String(preset.id),
    name: String(preset.name || "Untitled").slice(0, 120),
    config: { style: preset.style, body: preset.body, palette: preset.palette }
  }, { onConflict: "user_id,preset_id" });
  if (error) console.error("Cloud preset sync failed:", error.message);
}
async function restorePresets() {
  if (!state.client || !state.user) return;
  const { data, error } = await state.client.from("saved_presets")
    .select("preset_id,name,config,updated_at").order("updated_at", { ascending: false }).limit(100);
  if (error) { console.error("Could not load cloud presets:", error.message); return; }
  const local = JSON.parse(localStorage.getItem(presetStorageKey()) || "[]");
  const byId = new Map(local.map(x => [x.id, x]));
  for (const row of data || []) byId.set(row.preset_id, {
    id: row.preset_id, name: row.name, style: row.config?.style || "Normal",
    body: row.config?.body || "Balanced", palette: row.config?.palette || "#b8f36b"
  });
  localStorage.setItem(presetStorageKey(), JSON.stringify([...byId.values()].slice(0, 100)));
  window.dispatchEvent(new CustomEvent("forge:session-changed"));
}
async function init() {
  if (SUPABASE_CONFIGURED) {
    const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2.57.4");
    state.client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
    });
    const { data: { session }, error } = await state.client.auth.getSession();
    if (error) console.error("Session restore failed:", error.message);
    state.user = session?.user || null;
    if (state.user) await restorePresets();
    const recoveryLink = new URLSearchParams(location.hash.replace(/^#/, "")).get("type") === "recovery";
    state.client.auth.onAuthStateChange((event, sessionNow) => {
      state.user = sessionNow?.user || null;
      renderSession();
      if (event === "PASSWORD_RECOVERY") {
        setTimeout(() => showModal("recovery"), 0);
      }
      if (state.user) setTimeout(() => restorePresets(), 0);
    });
    if (recoveryLink && state.user) {
      history.replaceState(null, "", location.pathname + location.search);
      showModal("recovery");
    }
  }
  renderSession();
}
button.addEventListener("click", async () => {
  if (!state.user) return showModal("login");
  if (!state.client) return showModal("login");
  if (!confirm("Sign out of Forge 100K?")) return;
  const { error } = await state.client.auth.signOut();
  if (error) message(error.message, true);
  else { state.user = null; renderSession(); }
});
$("authClose").addEventListener("click", closeModal);
modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });
$("authSignupLink").addEventListener("click", e => { e.preventDefault(); showModal("signup"); });
$("authLoginLink").addEventListener("click", e => { e.preventDefault(); showModal("login"); });
$("authResetLink").addEventListener("click", e => { e.preventDefault(); showModal("reset"); });
form.addEventListener("submit", async e => {
  e.preventDefault();
  if (state.busy) return;
  if (!SUPABASE_CONFIGURED || !state.client) return message("Set SUPABASE_URL and SUPABASE_ANON_KEY in supabase-config.js first.", true);
  const email = $("authEmail").value.trim().toLowerCase();
  const password = $("authPassword").value;
  setBusy(true);
  try {
    if (state.mode === "signup") {
      const fullName = $("authName").value.trim();
      if (password.length < 12) throw new Error("Use a password with at least 12 characters.");
      if (password !== $("authConfirm").value) throw new Error("Passwords do not match.");
      const { data, error } = await state.client.auth.signUp({
        email, password, options: { data: { full_name: fullName } }
      });
      if (error) throw error;
      if (data.session) {
        state.user = data.user;
        message("Account created and signed in.");
        closeModal();
      } else {
        message("Account created. Check your email to verify the address before signing in.");
      }
    } else if (state.mode === "recovery") {
      if (password.length < 12) throw new Error("Use a password with at least 12 characters.");
      if (password !== $("authConfirm").value) throw new Error("Passwords do not match.");
      const { error } = await state.client.auth.updateUser({ password });
      if (error) throw error;
      message("Password updated successfully. You can now sign in with the new password.");
      closeModal();
    } else if (state.mode === "reset") {
      const { error } = await state.client.auth.resetPasswordForEmail(email, {
        redirectTo: location.origin + location.pathname
      });
      if (error) throw error;
      message("If the address belongs to an account, a password-reset email has been sent.");
    } else {
      const { data, error } = await state.client.auth.signInWithPassword({ email, password });
      if (error) throw error;
      state.user = data.user;
      await restorePresets();
      closeModal();
    }
  } catch (err) {
    message(err.message || "Authentication failed. Try again.", true);
  } finally {
    setBusy(false);
    renderSession();
  }
});
window.addEventListener("forge:preset-saved", e => syncPreset(e.detail));
init().catch(err => { console.error("Auth initialization failed:", err); message("Authentication could not initialize. Check project configuration."); });
