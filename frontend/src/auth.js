const SUPABASE_URL = "https://yjwitehnxbsmpusebqtt.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inlqd2l0ZWhueGJzbXB1c2VicXR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4OTkxNjUsImV4cCI6MjEwMDQ3NTE2NX0.hhFXuK7_5R3ByYeu9m2eRXB_d6DjkE2BcWidHJX-OWo";

let supabase = null;
let authAvailable = false;

try {
  if (window.supabase && window.supabase.createClient) {
    supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    authAvailable = true;
  }
} catch {
  console.warn("Supabase not available, running without auth");
}

export { supabase, authAvailable };

export async function signInWithGoogle() {
  if (!authAvailable) return null;
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: window.location.origin },
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
