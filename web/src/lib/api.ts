// Typed client for the ParkLens API. Base URL comes from NEXT_PUBLIC_API_URL.

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Child = { name: string; age: number; height_cm: number };
export type Party = {
  adults: number;
  children: Child[];
  interests: string[];
  hours_available: number;
  language: string;
  pace: "relaxed" | "normal" | "packed";
  start_time: string;
};
export type Eligibility = { ok: boolean; blocked: string[]; reason?: string | null };
export type Stop = {
  item_id: string;
  kind: "animal" | "attraction" | "break";
  name: string;
  start: string;
  minutes: number;
  why: string;
  source_url?: string | null;
  image?: string | null;
  eligibility?: Eligibility | null;
  walk_minutes?: number;
  lat?: number | null;
  lon?: number | null;
};
export type KbItem = {
  id: string; kind: "animal" | "attraction"; name: string; scientific_name?: string | null;
  image?: string | null; source_url: string; min_height_cm?: number | null;
  height_requirement?: string | null; lat?: number | null; lon?: number | null;
};
export type ParkMap = {
  park: string; entrance: { lat: number; lon: number };
  bounds: { min_lat: number; max_lat: number; min_lon: number; max_lon: number } | null;
};
export type Plan = { party: Party; stops: Stop[]; skipped: Stop[]; total_minutes: number; summary: string };
export type LensResult = {
  found: boolean;
  species_id?: string | null;
  species_name?: string | null;
  scientific_name?: string | null;
  confidence?: number | null;
  box?: { x1: number; y1: number; x2: number; y2: number; w: number; h: number; n_found: number } | null;
  narration: string;
  fun_fact: string;
  source_url?: string | null;
  language: string;
  cached: boolean;
};

async function check<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const j = await r.json();
      detail = j.detail ?? j.error ?? JSON.stringify(j);
    } catch {}
    throw new Error(`${r.status}: ${detail}`);
  }
  return r.json() as Promise<T>;
}

// Anonymous product events (no ids, no text, no images). Fire-and-forget.
export function track(name: string, props: Record<string, string | number | boolean> = {}) {
  try {
    fetch(`${API}/events`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, props }), keepalive: true }).catch(() => undefined);
  } catch {}
}

export const api = {
  items: () => fetch(`${API}/kb/items`).then((r) => check<KbItem[]>(r)),
  map: () => fetch(`${API}/kb/map`).then((r) => check<ParkMap>(r)),
  onboardText: (text: string) =>
    fetch(`${API}/onboard/text`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) }).then((r) => check<Party>(r)),
  onboardVoice: (audio: Blob) => {
    const fd = new FormData();
    fd.append("audio", audio, "voice.webm");
    return fetch(`${API}/onboard/voice`, { method: "POST", body: fd }).then((r) => check<{ transcript: string; party: Party }>(r));
  },
  transcribe: (audio: Blob) => {
    const fd = new FormData();
    fd.append("audio", audio, "voice.webm");
    return fetch(`${API}/transcribe`, { method: "POST", body: fd }).then((r) => check<{ text: string }>(r));
  },
  plan: (party: Party) =>
    fetch(`${API}/plan`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(party) }).then((r) => check<Plan>(r)),
  warm: (party: Party, species_ids: string[]) =>
    fetch(`${API}/lens/warm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ party, species_ids }) }).catch(() => undefined),
  replan: (plan: Plan, utterance: string, now: string, done_ids: string[]) =>
    fetch(`${API}/plan/replan`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plan, utterance, now, done_ids }) }).then((r) => check<Plan>(r)),
  lens: (image: Blob, party?: Party | null, hint?: string, expected?: string | null) => {
    const fd = new FormData();
    fd.append("image", image, "frame.jpg");
    if (party) fd.append("party", JSON.stringify(party));
    if (hint) fd.append("hint", hint);
    if (expected) fd.append("expected", expected);
    return fetch(`${API}/lens`, { method: "POST", body: fd }).then((r) => check<LensResult>(r));
  },
  timeTravel: (image: Blob, mode: "wild" | "ancestor" | "future", species_id?: string | null) => {
    const fd = new FormData();
    fd.append("image", image, "frame.jpg");
    fd.append("mode", mode);
    if (species_id) fd.append("species_id", species_id);
    return fetch(`${API}/timetravel`, { method: "POST", body: fd }).then((r) => check<{ image_b64: string; mime: string; label: string }>(r));
  },
};

// Tiny persistent store (per browser) for the party and plan.
export function load<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  try {
    const v = localStorage.getItem(`parklens:${key}`);
    return v ? (JSON.parse(v) as T) : null;
  } catch {
    return null;
  }
}
export function save(key: string, value: unknown) {
  try {
    localStorage.setItem(`parklens:${key}`, JSON.stringify(value));
  } catch {}
}

// "Now" for re-planning. Outside park hours (demos at midnight!) we pretend it's 13:00 so the
// new plan still reads like a day at the park. Override with localStorage parklens:clock=HH:MM.
export function nowHHMM() {
  const forced = load<string>("clock");
  if (forced) return forced;
  const d = new Date();
  const h = d.getHours();
  if (h < 9 || h > 18) return "13:00";
  return `${String(h).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function speak(text: string, lang: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = { en: "en-GB", sv: "sv-SE", fi: "fi-FI", de: "de-DE" }[lang] ?? lang;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

// React hook: read a stored value without a setState-in-effect (hydrates as null on the server).
import { useSyncExternalStore } from "react";
const listeners = new Set<() => void>();
function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => { listeners.delete(cb); window.removeEventListener("storage", cb); };
}
const cache = new Map<string, { raw: string | null; value: unknown }>();
export function useStored<T>(key: string): T | null {
  return useSyncExternalStore(
    subscribe,
    () => {
      const raw = (() => { try { return localStorage.getItem(`parklens:${key}`); } catch { return null; } })();
      const hit = cache.get(key);
      if (hit && hit.raw === raw) return hit.value as T | null;
      const value = raw ? (JSON.parse(raw) as T) : null;
      cache.set(key, { raw, value });
      return value;
    },
    () => null,
  );
}
export function saveStored(key: string, value: unknown) {
  save(key, value);
  listeners.forEach((cb) => cb());
}


// Compose a shareable before/after card (PNG blob) from two image URLs. Pure canvas, no deps.
export async function shareCard(beforeUrl: string, afterUrl: string, title: string, sub: string): Promise<Blob> {
  const load = (u: string) => new Promise<HTMLImageElement>((res, rej) => { const i = new Image(); i.crossOrigin = "anonymous"; i.onload = () => res(i); i.onerror = rej; i.src = u; });
  const [a, b] = await Promise.all([load(beforeUrl), load(afterUrl)]);
  const h = 720, gap = 16, pad = 32, foot = 110;
  const wa = Math.round((a.width / a.height) * h), wb = Math.round((b.width / b.height) * h);
  const c = document.createElement("canvas");
  c.width = pad * 2 + wa + gap + wb; c.height = pad + h + foot;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = "#052e16"; ctx.fillRect(0, 0, c.width, c.height);
  ctx.drawImage(a, pad, pad, wa, h); ctx.drawImage(b, pad + wa + gap, pad, wb, h);
  ctx.fillStyle = "rgba(0,0,0,.55)"; ctx.fillRect(pad, pad, 90, 34); ctx.fillRect(pad + wa + gap, pad, 230, 34);
  ctx.fillStyle = "#fff"; ctx.font = "bold 20px system-ui"; ctx.fillText("now", pad + 12, pad + 24); ctx.fillText(sub, pad + wa + gap + 12, pad + 24);
  ctx.font = "bold 34px system-ui"; ctx.fillText(title, pad, pad + h + 48);
  ctx.font = "20px system-ui"; ctx.fillStyle = "#a7f3d0"; ctx.fillText("ParkLens · AI artistic impression · built on Meta Muse models", pad, pad + h + 84);
  return new Promise((res) => c.toBlob((bl) => res(bl!), "image/png"));
}
