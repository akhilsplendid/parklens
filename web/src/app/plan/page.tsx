"use client";
import { useState } from "react";
import Link from "next/link";
import Recorder from "@/components/Recorder";
import { api, nowHHMM, saveStored, speak, useStored, type Plan } from "@/lib/api";

const ICON = { animal: "🐾", attraction: "🎢", break: "🧃" } as const;

export default function PlanPage() {
  const plan = useStored<Plan>("plan");
  const done = useStored<string[]>("done") ?? [];
  const [utter, setUtter] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function toggleDone(id: string) {
    const next = done.includes(id) ? done.filter((d) => d !== id) : [...done, id];
    saveStored("done", next);
  }

  async function replan(text: string) {
    if (!plan || !text.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const fresh = await api.replan(plan, text, nowHHMM(), done);
      saveStored("plan", fresh);
      saveStored("done", []);
      void api.warm(fresh.party, fresh.stops.filter((s) => s.kind === "animal").map((s) => s.item_id));
      setUtter("");
      if (fresh.summary) speak(fresh.summary, fresh.party.language);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!plan)
    return (
      <p className="text-neutral-600">
        No plan yet. <Link className="text-emerald-700 underline" href="/">Set up your family</Link> first.
      </p>
    );

  const hours = Math.round((plan.total_minutes / 60) * 10) / 10;
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-bold">Your day</h1>
        <p className="text-sm text-neutral-600 dark:text-neutral-400">{hours} h · {plan.stops.filter((s) => s.kind !== "break").length} stops</p>
        {plan.summary && <p className="mt-2 text-sm">{plan.summary}</p>}
      </header>

      <ol className="space-y-2">
        {plan.stops.map((s, i) => {
          const isDone = done.includes(s.item_id);
          return (
            <li key={`${s.item_id}-${i}`} className={`flex gap-3 rounded-2xl bg-white p-3 shadow-sm dark:bg-neutral-900 ${isDone ? "opacity-50" : ""}`}>
              <div className="w-12 shrink-0 text-right text-sm font-mono text-neutral-500">{s.start}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span>{ICON[s.kind]}</span>
                  <span className="font-semibold">{s.name}</span>
                  <span className="text-xs text-neutral-400">{s.minutes} min{s.walk_minutes ? ` · 🚶 ${s.walk_minutes}` : ""}</span>
                </div>
                {s.why && <p className="mt-1 text-sm text-neutral-700 dark:text-neutral-300">{s.why}</p>}
                <div className="mt-1 flex gap-3 text-xs">
                  {s.source_url && <a href={s.source_url} target="_blank" rel="noreferrer" className="text-emerald-700 underline">source</a>}
                  {s.kind !== "break" && (
                    <button onClick={() => toggleDone(s.item_id)} className="text-neutral-500 underline">{isDone ? "undo" : "done ✓"}</button>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>

      {plan.skipped.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40">
          <h2 className="font-semibold text-amber-900 dark:text-amber-200">Not this time</h2>
          <ul className="mt-1 space-y-1">
            {plan.skipped.map((s) => (
              <li key={s.item_id}>
                <span className="font-medium">{s.name}</span> <span className="text-amber-800 dark:text-amber-300">— {s.why}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-3 rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
        <h2 className="font-semibold">Something changed?</h2>
        <p className="text-xs text-neutral-500">Say &quot;we&apos;re tired, one hour left&quot; or &quot;skip the rides&quot;.</p>
        <Recorder disabled={busy} onAudio={async (b) => {
          setBusy(true);
          try {
            const { text } = await api.transcribe(b).catch(() => ({ text: "" }));
            if (text) await replan(text); else setErr("Couldn't hear that, try typing.");
          } finally { setBusy(false); }
        }} />
        <div className="flex gap-2">
          <input value={utter} onChange={(e) => setUtter(e.target.value)} placeholder="We're tired, one hour left"
                 className="flex-1 rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm dark:border-neutral-700 dark:bg-neutral-800" />
          <button disabled={busy || !utter.trim()} onClick={() => replan(utter)} className="rounded-xl bg-emerald-600 px-4 font-semibold text-white disabled:opacity-40">
            {busy ? "…" : "Re-plan"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {["We're tired, one hour left", "Kids want more rides", "Skip the animals we've seen"].map((q) => (
            <button key={q} onClick={() => replan(q)} disabled={busy} className="rounded-full border border-neutral-300 px-3 py-1 dark:border-neutral-700">{q}</button>
          ))}
        </div>
        {err && <p className="text-sm text-red-700">{err}</p>}
      </section>
    </div>
  );
}
