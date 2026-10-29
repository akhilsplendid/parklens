"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, Clock, Languages, Wand2 } from "lucide-react";
import Recorder from "@/components/Recorder";
import Art from "@/components/Art";
import { api, saveStored, track, useStored, type Party } from "@/lib/api";

const EXAMPLE = "Two adults, Mia is 5 and 110 cm, Leo is 9 and 135 cm. We love big cats and dolphins, we have five hours.";

export default function Onboard() {
  const router = useRouter();
  const party = useStored<Party>("party");
  const welcomed = useStored<boolean>("welcomed");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (welcomed === null && typeof window !== "undefined" && !localStorage.getItem("parklens:welcomed")) router.replace("/welcome");
  }, [welcomed, router]);

  async function run(fn: () => Promise<Party>) {
    setErr(null);
    try { saveStored("party", await fn()); } catch (e) { setErr(String(e)); } finally { setBusy(null); }
  }

  async function makePlan() {
    if (!party) return;
    setBusy("Planning your day…");
    try {
      const plan = await api.plan(party);
      track("plan_made", { demo: false, stops: plan.stops.length, children: party.children.length });
      saveStored("plan", plan); saveStored("done", []);
      void api.warm(party, plan.stops.filter((s) => s.kind === "animal").map((s) => s.item_id));
      router.push("/plan");
    } catch (e) { setErr(String(e)); setBusy(null); }
  }

  return (
    <div className="space-y-5">
      <header className="flex items-center gap-3">
        <Art name="icon" alt="" className="h-11 w-11 rounded-2xl" />
        <div>
          <h1 className="text-2xl font-black leading-tight">Who&apos;s visiting?</h1>
          <p className="text-sm text-muted">I&apos;ll plan a day that fits your kids.</p>
        </div>
      </header>

      <section className="card space-y-3 p-4">
        <Recorder disabled={!!busy} onAudio={(b) => { setBusy("Listening…"); run(async () => (await api.onboardVoice(b)).party); }} />
        <div className="text-center text-xs font-bold uppercase tracking-wide text-muted">or type</div>
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={EXAMPLE} rows={3} className="input" />
        <div className="flex gap-2">
          <button disabled={!!busy || !text.trim()} onClick={() => { setBusy("Reading…"); run(() => api.onboardText(text)); }} className="btn btn-primary flex-1">Set up my family</button>
          <button onClick={() => setText(EXAMPLE)} className="btn btn-ghost" aria-label="Fill example"><Wand2 size={18} /></button>
        </div>
      </section>

      {busy && <p className="animate-pulse text-center text-sm font-bold text-forest">{busy}</p>}
      {err && <p className="rounded-2xl bg-red-50 p-3 text-sm text-danger">{err}</p>}

      {party && (
        <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card space-y-4 p-4">
          <h2 className="font-extrabold">Your group</h2>
          <ul className="flex flex-wrap gap-2">
            <li className="chip chip-muted">{party.adults} adult{party.adults === 1 ? "" : "s"}</li>
            {party.children.map((c) => <li key={c.name} className="chip chip-forest">{c.name} · {c.age} y · {c.height_cm} cm</li>)}
            {party.interests.map((i) => <li key={i} className="chip chip-amber">{i}</li>)}
            <li className="chip chip-sky"><Clock size={14} /> {party.hours_available} h</li>
            <li className="chip chip-sky"><Languages size={14} /> {party.language.toUpperCase()}</li>
          </ul>
          <button onClick={makePlan} disabled={!!busy} className="btn btn-amber w-full">Plan our day <ArrowRight size={20} /></button>
        </motion.section>
      )}
    </div>
  );
}
