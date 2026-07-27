const SUPABASE_URL = "https://yjwitehnxbsmpusebqtt.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlqd2l0ZWhueGJzbXB1c2VicXR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4OTkxNjUsImV4cCI6MjEwMDQ3NTE2NX0.hhFXuK7_5R3ByYeu9m2eRXB_d6DjkE2BcWidHJX-OWo";

let supabase = null;
let authAvailable = false;

function ensureSupabase() {
  if (supabase) return true;
  try {
    if (window.supabase && window.supabase.createClient) {
      supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
      authAvailable = true;
      return true;
    }
  } catch {
    console.warn("Supabase init failed");
  }
  return false;
}

try {
  ensureSupabase();
} catch {
  console.warn("Supabase not available, running without auth");
}

if (!authAvailable) {
  window.addEventListener("load", () => {
    ensureSupabase();
  });
}

export { supabase, authAvailable };

export async function signInWithGoogle() {
  ensureSupabase();
  if (!authAvailable) {
    console.error("Supabase not loaded. Check your network connection.");
    throw new Error("No se pudo conectar con el servicio de autenticación. Verifica tu conexión a internet.");
  }
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin,
      scopes: "openid email profile",
    },
  });
  if (error) throw error;
  return data;
}

export async function signOut() {
  if (!authAvailable) return;
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error("timeout")), ms)),
  ]);
}

export async function getCurrentUser() {
  if (!authAvailable) return null;
  try {
    const { data: { session } } = await withTimeout(supabase.auth.getSession(), 3000);
    return session?.user || null;
  } catch {
    return null;
  }
}

export async function getSession() {
  if (!authAvailable) return null;
  try {
    const { data: { session } } = await withTimeout(supabase.auth.getSession(), 3000);
    return session;
  } catch {
    return null;
  }
}

export async function saveToHistory(dataset, analysis, actions, before, after, reportPdfBase64) {
  if (!authAvailable || !supabase) return null;
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const user = session?.user;
    if (!user) return null;

    const { data: ds, error: dsErr } = await supabase
      .from("datasets")
      .insert({
        user_id: user.id,
        filename: dataset.filename || "dataset",
        content_base64: "not_stored",
        row_count: dataset.row_count || 0,
        column_count: dataset.column_count || 0,
      })
      .select()
      .single();
    if (dsErr) throw dsErr;

    if (analysis) {
      const { error: aErr } = await supabase
        .from("analyses")
        .insert({
          dataset_id: ds.id,
          user_id: user.id,
          analysis_json: analysis,
          row_meaning: dataset.row_meaning || "",
          analysis_objective: dataset.analysis_objective || "",
        });
      if (aErr) throw aErr;
    }

    if (actions && actions.length > 0) {
      const { error: cErr } = await supabase
        .from("cleaning_sessions")
        .insert({
          dataset_id: ds.id,
          user_id: user.id,
          actions_json: actions,
          before_json: before || null,
          after_json: after || null,
          report_pdf_base64: reportPdfBase64 || "",
        });
      if (cErr) throw cErr;
    }

    return ds.id;
  } catch (e) {
    console.warn("Failed to save to history:", e);
    return null;
  }
}

export async function getHistory() {
  if (!authAvailable || !supabase) return [];
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const user = session?.user;
    if (!user) return [];

    const { data, error } = await supabase
      .from("cleaning_sessions")
      .select("id, created_at, actions_json, before_json, after_json, report_pdf_base64, datasets!inner(filename, row_count, column_count)")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(20);
    if (error) throw error;
    return data || [];
  } catch (e) {
    console.warn("Failed to load history:", e);
    return [];
  }
}

export async function getHistorySession(sessionId) {
  if (!authAvailable || !supabase) return null;
  try {
    const { data: { session } } = await supabase.auth.getSession();
    const user = session?.user;
    if (!user) return null;

    const { data, error } = await supabase
      .from("cleaning_sessions")
      .select("*, datasets!inner(filename, row_count, column_count)")
      .eq("id", sessionId)
      .eq("user_id", user.id)
      .single();
    if (error) throw error;
    return data;
  } catch (e) {
    console.warn("Failed to load session:", e);
    return null;
  }
}
