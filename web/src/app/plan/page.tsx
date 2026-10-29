"use client";
import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { PawPrint, FerrisWheel, Coffee, Footprints, Check, Undo2, ExternalLink, RefreshCw } from "lucide-react";
import Recorder from "@/components/Recorder";
import Art from "@/components/Art";
import { api, errMsg, nowHHMM, track, saveStored, speak, useStored, type Plan } from "@/lib/api";
import { Clock } from "lucide-react";

const ICON = { animal: PawPrint, attraction: FerrisWheel, break: Coffee } as const;
const TONE = { animal: "text-sky bg-sky-soft", attraction: "text-amber bg-amber-soft", break: "text-forest bg-forest-soft" } as const;

export default function PlanPage() {
  const plan = useStored<Plan>("plan");
  const done = useStored<string[]>("done") ?? [];
  const [utter, setUtter] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const clock = useStored<string>("clock");
  // Demo clock: re-planning uses "now"; tap the time to pretend it's later in the day.
  function bumpClock() {
    const order = [null, "13:00", "15:00", "17:00"];
    const next = order[(order.indexOf(clock) + 1) % order.length];
    saveStored("clock", next);
  }

  function toggleDone(id: string) {
    saveStored("done", done.includes(id) ? done.filter((d) => d !== id) : [...done, id]);
  }

  async function replan(text: string) {
    if (!plan || !text.trim()) return;
    setBusy(true); setErr(null);
    try {
      const fresh = await api.replan(plan, text, nowHHMM(), done);
      track("replan", { stops: fresh.stops.length });
      saveStored("plan", fresh); saveStored("done", []);
      void api.warm(fresh.party, fresh.stops.filter((s) => s.kind === "animal").map((s) => s.item_id));
      setUtter("");
      if (fresh.summary) speak(fresh.summary, fresh.party.language);
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(false); }
  }

  if (!plan)
    return (
      <div className="space-y-4 pt-6 text-center">
        <Art name="welcome-plan" alt="" className="mx-auto aspect-[3/2] w-full" />
        <p className="text-muted">No plan yet. <Link className="font-extrabold text-forest underline" href="/">Set up your family</Link> first.</p>
      </div>
    );

  const hours = Math.round((plan.total_minutes / 60) * 10) / 10;
  const walk = plan.stops.reduce((a, s) => a + (s.walk_minutes ?? 0), 0);
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-black">Your day</h1>
        <p className="text-sm text-muted">{hours} h · {plan.stops.filter((s) => s.kind !== "break").length} stops · {walk} min walking</p>
        {plan.summary && <p className="mt-2 text-[15px] leading-relaxed">{plan.summary}</p>}
      </header>

      <ol className="relative space-y-2 pl-1">
        <span className="absolute bottom-6 left-[2.35rem] top-6 w-0.5 bg-line" aria-hidden />
        {plan.stops.map((s, i) => {
          const Icon = ICON[s.kind];
          const isDone = done.includes(s.item_id);
          return (
            <motion.li key={`${s.item_id}-${i}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i * 0.05, 0.5) }}
              className={`relative flex gap-3 ${isDone ? "opacity-45" : ""}`}>
              <div className="w-11 shrink-0 pt-3 text-right font-mono text-xs text-muted">{s.start}</div>
              <div className={`z-10 mt-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${TONE[s.kind]}`}><Icon size={16} /></div>
              <div className="card flex-1 p-3">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-extrabold">{s.name}</span>
                  <span className="shrink-0 text-xs text-muted">{s.minutes} min{s.walk_minutes ? <> · <Footprints size={12} className="inline" /> {s.walk_minutes}</> : null}</span>
                </div>
                {s.why && <p className="mt-1 text-sm leading-relaxed">{s.why}</p>}
                {s.kind !== "break" && (
                  <div className="mt-2 flex gap-3 text-xs font-bold">
                    {s.source_url && <a href={s.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-forest">source <ExternalLink size={12} /></a>}
                    <button onClick={() => toggleDone(s.item_id)} className="inline-flex items-center gap-1 text-muted">{isDone ? <><Undo2 size={12} /> undo</> : <><Check size={12} /> done</>}</button>
                  </div>
                )}
              </div>
            </motion.li>
          );
        })}
      </ol>

      {plan.skipped.length > 0 && (
        <section className="rounded-2xl border border-amber/40 bg-amber-soft p-4 text-sm">
          <h2 className="font-extrabold text-[#92400e]">Not this time</h2>
          <ul className="mt-1 space-y-1">
            {plan.skipped.map((s) => <li key={s.item_id}><span className="font-bold">{s.name}</span> <span className="text-[#92400e]">— {s.why}</span></li>)}
          </ul>
          <p className="mt-2 text-xs text-[#92400e]/80">Height and age rules come from the park&apos;s own pages and are checked in code, never guessed.</p>
        </section>
      )}

      <section className="card space-y-3 p-4">
        <h2 className="flex items-center gap-2 font-extrabold"><RefreshCw size={18} className="text-forest" /> Something changed?</h2>
        <p className="text-xs text-muted">Say &quot;we&apos;re tired, one hour left&quot; or &quot;skip the rides&quot;.</p>
        <Recorder disabled={busy} onAudio={async (b) => {
          setBusy(true);
          try {
            const { text } = await api.transcribe(b).catch(() => ({ text: "" }));
            if (text) await replan(text); else setErr("Couldn't hear that, try typing.");
          } finally { setBusy(false); }
        }} />
        <div className="flex gap-2">
          <input value={utter} onChange={(e) => setUtter(e.target.value)} placeholder="We're tired, one hour left" className="input" />
          <button disabled={busy || !utter.trim()} onClick={() => replan(utter)} className="btn btn-primary shrink-0">{busy ? "…" : "Re-plan"}</button>
        </div>
        <div className="flex flex-wrap gap-2">
          {["We're tired, one hour left", "Kids want more rides", "Skip the animals we've seen"].map((q) => (
            <button key={q} onClick={() => replan(q)} disabled={busy} className="chip chip-muted">{q}</button>
          ))}
        </div>
        {err && <p className="text-sm text-danger">{err}</p>}
        <button onClick={bumpClock} className="flex items-center gap-1 text-xs text-muted" title="Demo clock: tap to pretend it's later">
          <Clock className="h-3.5 w-3.5" /> It&apos;s {nowHHMM()}{clock ? " (demo clock)" : ""}
        </button>
      </section>
    </div>
  );
}
