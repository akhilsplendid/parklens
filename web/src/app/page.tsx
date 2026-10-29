"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Recorder from "@/components/Recorder";
import { api, saveStored, useStored, type Party } from "@/lib/api";

const EXAMPLE = "Two adults, Mia is 5 and 110 cm, Leo is 9 and 135 cm. We love big cats and dolphins, we have five hours.";

export default function Onboard() {
  const router = useRouter();
  const [text, setText] = useState("");
  const party = useStored<Party>("party");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run(fn: () => Promise<Party>) {
    setErr(null);
    try {
      const p = await fn();
      saveStored("party", p);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(null);
    }
  }

  async function makePlan() {
    if (!party) return;
    setBusy("Planning your day…");
    try {
      const plan = await api.plan(party);
      saveStored("plan", plan);
      saveStored("done", []);
      // Pre-generate narration for today's animals so the Lens answers fast on the first look.
      void api.warm(party, plan.stops.filter((s) => s.kind === "animal").map((s) => s.item_id));
      router.push("/plan");
    } catch (e) {
      setErr(String(e));
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold">ParkLens</h1>
        <p className="text-neutral-600 dark:text-neutral-400">Tell me who&apos;s visiting and I&apos;ll plan a day that fits your kids.</p>
      </header>

      <section className="rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
        <Recorder disabled={!!busy} onAudio={(b) => { setBusy("Listening…"); run(async () => (await api.onboardVoice(b)).party); }} />
        <div className="my-3 text-center text-xs text-neutral-400">or type</div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={EXAMPLE}
          rows={3}
          className="w-full rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm dark:border-neutral-700 dark:bg-neutral-800"
        />
        <div className="mt-2 flex gap-2">
          <button
            disabled={!!busy || !text.trim()}
            onClick={() => { setBusy("Reading…"); run(() => api.onboardText(text)); }}
            className="flex-1 rounded-xl bg-emerald-600 py-3 font-semibold text-white disabled:opacity-40"
          >
            Set up my family
          </button>
          <button onClick={() => setText(EXAMPLE)} className="rounded-xl border border-neutral-300 px-3 text-sm dark:border-neutral-700">Example</button>
        </div>
      </section>

      {busy && <p className="animate-pulse text-center text-sm text-emerald-700">{busy}</p>}
      {err && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{err}</p>}

      {party && (
        <section className="space-y-3 rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
          <h2 className="font-semibold">Your group</h2>
          <ul className="flex flex-wrap gap-2 text-sm">
            <li className="rounded-full bg-neutral-100 px-3 py-1 dark:bg-neutral-800">{party.adults} adult{party.adults === 1 ? "" : "s"}</li>
            {party.children.map((c) => (
              <li key={c.name} className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200">
                {c.name}, {c.age} y · {c.height_cm} cm
              </li>
            ))}
            {party.interests.map((i) => (
              <li key={i} className="rounded-full bg-amber-50 px-3 py-1 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{i}</li>
            ))}
            <li className="rounded-full bg-neutral-100 px-3 py-1 dark:bg-neutral-800">{party.hours_available} h · {party.language.toUpperCase()}</li>
          </ul>
          <button onClick={makePlan} disabled={!!busy} className="w-full rounded-xl bg-neutral-900 py-3 font-semibold text-white dark:bg-white dark:text-black disabled:opacity-40">
            Plan our day →
          </button>
        </section>
      )}
    </div>
  );
}
