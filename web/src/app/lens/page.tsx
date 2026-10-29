"use client";
import { useEffect, useRef, useState } from "react";
import { api, shareCard, speak, useStored, type LensResult, type Party } from "@/lib/api";

type TT = { mode: "wild" | "ancestor" | "future"; url: string; label: string };
const MODES: { mode: TT["mode"]; label: string; icon: string }[] = [
  { mode: "wild", label: "In the wild", icon: "🌍" },
  { mode: "ancestor", label: "1 million years ago", icon: "🦣" },
  { mode: "future", label: "100 years ahead", icon: "🌱" },
];

export default function Lens() {
  const video = useRef<HTMLVideoElement>(null);
  const party = useStored<Party>("party");
  const here = useStored<string>("here");
  const [camOk, setCamOk] = useState<boolean | null>(null);
  const [frame, setFrame] = useState<{ blob: Blob; url: string; w: number; h: number } | null>(null);
  const [result, setResult] = useState<LensResult | null>(null);
  const [tt, setTt] = useState<TT | null>(null);
  const [slider, setSlider] = useState(50);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let stream: MediaStream | undefined;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } }, audio: false })
      .then((s) => { stream = s; if (video.current) { video.current.srcObject = s; } setCamOk(true); })
      .catch(() => setCamOk(false));
    return () => stream?.getTracks().forEach((t) => t.stop());
  }, []);

  function capture() {
    const v = video.current;
    if (!v || !v.videoWidth) return;
    const c = document.createElement("canvas");
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d")!.drawImage(v, 0, 0);
    c.toBlob((b) => b && analyze(b, c.width, c.height), "image/jpeg", 0.9);
  }

  function onFile(f: File | undefined) {
    if (!f) return;
    const url = URL.createObjectURL(f);
    const img = new Image();
    img.onload = () => analyze(f, img.naturalWidth, img.naturalHeight, url);
    img.src = url;
  }

  async function analyze(blob: Blob, w: number, h: number, url = URL.createObjectURL(blob)) {
    setFrame({ blob, url, w, h });
    setResult(null); setTt(null); setErr(null);
    setBusy("Looking…");
    try {
      const r = await api.lens(blob, party, undefined, here);
      setResult(r);
      if (r.found && r.species_id) speak(`${r.narration} ${r.fun_fact}`, r.language);
    } catch (e) { setErr(String(e)); } finally { setBusy(null); }
  }

  async function timeTravel(mode: TT["mode"]) {
    if (!frame) return;
    setBusy("Painting…"); setErr(null);
    try {
      const r = await api.timeTravel(frame.blob, mode, result?.species_id);
      setTt({ mode, url: `data:${r.mime};base64,${r.image_b64}`, label: r.label });
      setSlider(50);
    } catch (e) { setErr(String(e)); } finally { setBusy(null); }
  }

  async function share() {
    if (!frame || !tt || !result) return;
    const label = MODES.find((m) => m.mode === tt.mode)?.label ?? tt.mode;
    const png = await shareCard(frame.url, tt.url, `${result.species_name} · ${label}`, label);
    const file = new File([png], "parklens.png", { type: "image/png" });
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], title: "ParkLens", text: `${result.species_name}, ${label}. #ParkLens #MetaHackathon` }).catch(() => {});
    } else {
      const a = document.createElement("a"); a.href = URL.createObjectURL(png); a.download = "parklens.png"; a.click();
    }
  }

  // Box overlay in percent of the frame (SAM reports coords on the downscaled frame).
  const box = result?.box && frame ? {
    left: `${(result.box.x1 / result.box.w) * 100}%`, top: `${(result.box.y1 / result.box.h) * 100}%`,
    width: `${((result.box.x2 - result.box.x1) / result.box.w) * 100}%`, height: `${((result.box.y2 - result.box.y1) / result.box.h) * 100}%`,
  } : null;

  return (
    <div className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold">Lens</h1>
        <span className="text-xs text-neutral-500">{party ? `for ${party.children[0]?.name ?? "you"} · ${party.language.toUpperCase()}` : "no family set"}{here ? ` · 📍 ${here}` : ""}</span>
      </header>

      {/* Viewfinder or captured frame */}
      <div className="relative overflow-hidden rounded-2xl bg-black" style={{ aspectRatio: frame ? `${frame.w}/${frame.h}` : "4/3" }}>
        {!frame && <video ref={video} autoPlay playsInline muted className="h-full w-full object-cover" />}
        {frame && !tt && <img src={frame.url} alt="captured" className="h-full w-full object-contain" />}
        {frame && tt && (
          <div className="relative h-full w-full select-none">
            <img src={frame.url} alt="now" className="absolute inset-0 h-full w-full object-contain" />
            <img src={tt.url} alt={tt.label} className="absolute inset-0 h-full w-full object-contain" style={{ clipPath: `inset(0 0 0 ${slider}%)` }} />
            <div className="absolute inset-y-0 w-0.5 bg-white" style={{ left: `${slider}%` }} />
            <input type="range" min={0} max={100} value={slider} onChange={(e) => setSlider(+e.target.value)} className="absolute inset-x-0 bottom-2 w-full" aria-label="before / after" />
            <span className="absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">now</span>
            <span className="absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">{MODES.find((m) => m.mode === tt.mode)?.label} · AI art</span>
          </div>
        )}
        {box && !tt && (
          <div className="absolute rounded-lg border-[3px] border-emerald-400 shadow-[0_0_0_9999px_rgba(0,0,0,0.25)]" style={box}>
            <span className="absolute -top-6 left-0 rounded bg-emerald-500 px-2 py-0.5 text-xs font-semibold text-white">{result?.species_name}</span>
          </div>
        )}
        {busy && <div className="absolute inset-0 flex items-center justify-center bg-black/40 text-white animate-pulse">{busy}</div>}
        {camOk === false && !frame && <div className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-white">Camera unavailable (needs HTTPS). Use the photo button below.</div>}
      </div>

      <div className="flex items-center justify-center gap-4">
        {!frame ? (
          <button onClick={capture} disabled={!camOk || !!busy} className="h-16 w-16 rounded-full border-4 border-white bg-emerald-600 shadow-lg disabled:opacity-40" aria-label="Capture" />
        ) : (
          <button onClick={() => { setFrame(null); setResult(null); setTt(null); }} className="rounded-xl bg-neutral-900 px-5 py-3 font-semibold text-white dark:bg-white dark:text-black">↺ New look</button>
        )}
        <label className="cursor-pointer rounded-xl border border-neutral-300 px-4 py-3 text-sm dark:border-neutral-700">
          📁 Photo
          <input type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
        </label>
      </div>

      {err && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{err}</p>}

      {result && (
        <section className="space-y-3 rounded-2xl bg-white p-4 shadow-sm dark:bg-neutral-900">
          {result.found && result.species_id ? (
            <>
              <div className="flex items-baseline justify-between">
                <h2 className="text-xl font-bold">{result.species_name}</h2>
                <span className="text-xs italic text-neutral-500">{result.scientific_name}</span>
              </div>
              <p className="text-base leading-relaxed">{result.narration}</p>
              <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-900/30 dark:text-amber-100">💡 {result.fun_fact}</p>
              <div className="flex items-center justify-between text-xs text-neutral-500">
                {result.source_url && <a href={result.source_url} target="_blank" rel="noreferrer" className="underline">Source: park page</a>}
                <button onClick={() => speak(`${result.narration} ${result.fun_fact}`, result.language)} className="underline">🔊 read again</button>
              </div>
              {tt && (
                <button onClick={share} className="w-full rounded-xl bg-emerald-600 py-2 text-sm font-semibold text-white">⬆️ Share before / after</button>
              )}
              <div className="grid grid-cols-3 gap-2 pt-1">
                {MODES.map((m) => (
                  <button key={m.mode} onClick={() => timeTravel(m.mode)} disabled={!!busy}
                          className={`rounded-xl border p-2 text-xs ${tt?.mode === m.mode ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/30" : "border-neutral-200 dark:border-neutral-700"} disabled:opacity-40`}>
                    <div className="text-xl">{m.icon}</div>{m.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <p className="text-sm">{result.narration}</p>
              {result.found && (
                <p className="text-xs text-neutral-500">ParkLens only tells stories it can back with the park&apos;s own pages, so it won&apos;t guess about this one.</p>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}
