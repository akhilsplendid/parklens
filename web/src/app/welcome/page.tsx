"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import Art from "@/components/Art";
import { api, errMsg, saveStored, track } from "@/lib/api";

const SLIDES = [
  { art: "welcome-family", title: "Tell me who's coming", text: "Say it or type it: ages, heights, what the kids love, how long you have." },
  { art: "welcome-plan", title: "Get a day that fits", text: "Rides your kids are tall enough for, breaks before meltdowns, and a route that saves little legs." },
  { art: "welcome-lens", title: "Point at an animal", text: "ParkLens finds it, tells its story from the park's own facts in your language, and shows it in the wild or a million years ago." },
];

const DEMO_FAMILY = "Two adults, Mia is 5 and 110 cm, Leo is 9 and 135 cm. We love big cats and dolphins, we have five hours.";

export default function Welcome() {
  const router = useRouter();
  const [i, setI] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const last = i === SLIDES.length - 1;

  async function demo() {
    setBusy(true); setErr(null);
    try {
      const party = await api.onboardText(DEMO_FAMILY);
      saveStored("party", party);
      const plan = await api.plan(party);
      track("plan_made", { demo: true, stops: plan.stops.length });
      saveStored("plan", plan);
      saveStored("done", []);
      void api.warm(party, plan.stops.filter((s) => s.kind === "animal").map((s) => s.item_id));
      saveStored("welcomed", true);
      router.push("/plan");
    } catch (e) {
      setErr(errMsg(e));
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-2rem)] flex-col justify-between py-2">
      <div className="flex items-center gap-2 text-forest">
        <Art name="icon" alt="" className="h-9 w-9 rounded-xl" />
        <span className="text-xl font-black">ParkLens</span>
      </div>

      <AnimatePresence mode="wait">
        <motion.section key={i} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} transition={{ duration: 0.25 }} className="space-y-5">
          <Art name={SLIDES[i].art} alt={SLIDES[i].title} className="aspect-[3/2] w-full" />
          <h1 className="text-3xl font-black leading-tight">{SLIDES[i].title}</h1>
          <p className="text-lg text-muted">{SLIDES[i].text}</p>
        </motion.section>
      </AnimatePresence>

      <div className="space-y-3">
        <div className="flex justify-center gap-1.5">
          {SLIDES.map((_, n) => <span key={n} className={`h-2 rounded-full transition-all ${n === i ? "w-6 bg-forest" : "w-2 bg-line"}`} />)}
        </div>
        {last ? (
          <>
            <button onClick={() => { saveStored("welcomed", true); router.push("/"); }} className="btn btn-primary w-full">Set up my family <ArrowRight size={20} /></button>
            <button onClick={demo} disabled={busy} className="btn btn-ghost w-full"><Sparkles size={18} /> {busy ? "Planning the demo day…" : "Try with a demo family"}</button>
            {err && <p className="text-center text-sm text-danger">{err}</p>}
          </>
        ) : (
          <button onClick={() => setI(i + 1)} className="btn btn-primary w-full">Next <ArrowRight size={20} /></button>
        )}
        {!last && <button onClick={() => { saveStored("welcomed", true); router.push("/"); }} className="w-full py-1 text-sm text-muted">Skip</button>}
      </div>
    </div>
  );
}
