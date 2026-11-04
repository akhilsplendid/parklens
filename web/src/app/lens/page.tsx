"use client";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Camera, Image as ImageIcon, RotateCcw, Share2, Volume2, ExternalLink, Globe2, Mountain, Sprout, Lightbulb } from "lucide-react";
import { api, errMsg, shareCard, track, speak, stopSpeaking, unlockSpeech, useStored, type LensResult, type Party } from "@/lib/api";

type TT = { mode: "wild" | "ancestor" | "future"; url: string; label: string };
const MODES: { mode: TT["mode"]; label: string; Icon: typeof Globe2 }[] = [
  { mode: "wild", label: "In the wild", Icon: Globe2 },
  { mode: "ancestor", label: "1 million years ago", Icon: Mountain },
  { mode: "future", label: "100 years ahead", Icon: Sprout },
];

export default function Lens() {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const party = useStored<Party>("party");
  const here = useStored<string>("here");
  const [camOk, setCamOk] = useState<boolean | null>(null);
  const [camErr, setCamErr] = useState<string>("");
  const [frame, setFrame] = useState<{ blob: Blob; url: string; w: number; h: number } | null>(null);
  const [result, setResult] = useState<LensResult | null>(null);
  const [tt, setTt] = useState<TT | null>(null);
  const [slider, setSlider] = useState(50);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const fail = (msg: string) => { setCamOk(false); setCamErr(msg); };
    const open = async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        fail(window.isSecureContext ? "No camera on this device. Use Photo." : "Camera needs HTTPS. Use Photo."); return;
      }
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } }, audio: false });
        stream.current = s; if (video.current) video.current.srcObject = s; setCamOk(true);
      } catch (e) {
        fail((e as DOMException)?.name === "NotAllowedError" ? "Camera permission denied. Allow it in your browser settings, or use Photo." : "Camera unavailable. Use Photo.");
      }
    };
    void open();
    return () => { stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null; stopSpeaking(); };
  }, []);

  // The <video> is unmounted while a frame is shown; re-attach the live stream on "New look".
  useEffect(() => {
    if (!frame && video.current && stream.current && video.current.srcObject !== stream.current) video.current.srcObject = stream.current;
  }, [frame]);

  function capture() {
    unlockSpeech();
    const v = video.current;
    if (!v || !v.videoWidth) { setErr("Camera is still starting. Try again in a second."); return; }
    const c = document.createElement("canvas");
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d")!.drawImage(v, 0, 0);
    c.toBlob((b) => b && analyze(b, c.width, c.height), "image/jpeg", 0.9);
  }

  // Gallery photo: honour EXIF rotation and shrink a 12 MP shot before upload (cellular!).
  async function onFile(f: File | undefined) {
    if (!f) return;
    unlockSpeech();
    try {
      const bmp = await createImageBitmap(f, { imageOrientation: "from-image" });
      const scale = Math.min(1, 1280 / Math.max(bmp.width, bmp.height));
      const c = document.createElement("canvas");
      c.width = Math.round(bmp.width * scale); c.height = Math.round(bmp.height * scale);
      c.getContext("2d")!.drawImage(bmp, 0, 0, c.width, c.height);
      bmp.close?.();
      c.toBlob((b) => b && analyze(b, c.width, c.height), "image/jpeg", 0.9);
    } catch {
      setErr("Couldn't read that image. Try a JPEG or PNG.");
    }
  }

  async function analyze(blob: Blob, w: number, h: number, url = URL.createObjectURL(blob)) {
    setFrame({ blob, url, w, h });
    setResult(null); setTt(null); setErr(null);
    setBusy("Looking…");
    const t0 = performance.now();
    try {
      const r = await api.lens(blob, party, undefined, here);
      track(r.species_id ? "lens_hit" : "lens_miss", { ms: Math.round(performance.now() - t0), expected: !!here });
      setResult(r);
      if (r.found && r.species_id) speak(`${r.narration} ${r.fun_fact}`, r.language);
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(null); }
  }

  async function timeTravel(mode: TT["mode"]) {
    if (!frame) return;
    setBusy("Painting…"); setErr(null);
    try {
      const r = await api.timeTravel(frame.blob, mode, result?.species_id, result?.box);
      track("timetravel", { mode });
      setTt({ mode, url: `data:${r.mime};base64,${r.image_b64}`, label: r.label });
      setSlider(50);
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(null); }
  }

  async function share() {
    if (!frame || !tt || !result) return;
    const label = MODES.find((m) => m.mode === tt.mode)?.label ?? tt.mode;
    track("share", { mode: tt.mode });
    setBusy("Making card…"); setErr(null);
    const download = (png: Blob) => { const a = document.createElement("a"); a.href = URL.createObjectURL(png); a.download = "parklens.png"; a.click(); };
    try {
      const png = await shareCard(frame.url, tt.url, `${result.species_name} · ${label}`, label);
      const file = new File([png], "parklens.png", { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({ files: [file], title: "ParkLens", text: `${result.species_name}, ${label}. #ParkLens #MetaHackathon` });
        } catch (e) {
          if ((e as Error).name !== "AbortError") download(png); // share sheet refused → save the card
        }
      } else download(png);
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(null); }
  }

  // Box overlay in percent of the frame (SAM reports coords on the downscaled frame).
  const box = result?.box && frame ? {
    left: `${(result.box.x1 / result.box.w) * 100}%`, top: `${(result.box.y1 / result.box.h) * 100}%`,
    width: `${((result.box.x2 - result.box.x1) / result.box.w) * 100}%`, height: `${((result.box.y2 - result.box.y1) / result.box.h) * 100}%`,
  } : null;

  return (
    <div className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-black">Lens</h1>
        <span className="text-xs text-muted">{party ? `for ${party.children[0]?.name ?? "you"} · ${party.language.toUpperCase()}` : "no family set"}{here ? ` · 📍 ${here}` : ""}</span>
      </header>

      {/* Viewfinder or captured frame */}
      <div className="relative overflow-hidden rounded-[20px] bg-black shadow-lg" style={{ aspectRatio: frame ? `${frame.w}/${frame.h}` : "4/3" }}>
        {!frame && <video ref={video} autoPlay playsInline muted className="h-full w-full object-cover" />}
        {frame && !tt && <img src={frame.url} alt="captured" className="h-full w-full object-contain" />}
        {frame && tt && (
          <div className="relative h-full w-full select-none wipe">
            <img src={frame.url} alt="now" className="absolute inset-0 h-full w-full object-contain" />
            <img src={tt.url} alt={tt.label} className="absolute inset-0 h-full w-full object-contain" style={{ clipPath: `inset(0 0 0 ${slider}%)` }} />
            <div className="absolute inset-y-0 w-0.5 bg-white" style={{ left: `${slider}%` }} />
            <input type="range" min={0} max={100} value={slider} onChange={(e) => setSlider(+e.target.value)} className="absolute inset-x-0 bottom-2 w-full" aria-label="before / after" />
            <span className="absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">now</span>
            <span className="absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">{MODES.find((m) => m.mode === tt.mode)?.label} · AI art</span>
          </div>
        )}
        {box && !tt && (
          <motion.div initial={{ opacity: 0, scale: 1.08 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: "spring", stiffness: 260, damping: 20 }}
            className="absolute rounded-xl border-[3px] border-emerald-400 shadow-[0_0_0_9999px_rgba(0,0,0,0.28)]" style={box}>
            <span className={`absolute left-0 rounded-lg bg-emerald-500 px-2 py-0.5 text-xs font-extrabold text-white ${result && result.box && result.box.y1 / result.box.h < 0.1 ? "top-1 left-1" : "-top-7"}`}>{result?.species_name}</span>
          </motion.div>
        )}
        {busy && (
          <div className="absolute inset-0 bg-black/30">
            {busy === "Looking…" && <div className="scanline" />}
            <div className="absolute inset-x-0 bottom-3 text-center text-sm font-extrabold text-white drop-shadow">{busy}</div>
          </div>
        )}
        {camOk === false && !frame && <div className="absolute inset-0 flex items-center justify-center p-4 text-center text-sm text-white">{camErr}</div>}
        {camOk === null && !frame && !busy && <div className="absolute inset-x-0 bottom-3 text-center text-xs text-white/80">Starting camera…</div>}
      </div>

      <div className="flex items-center justify-center gap-4">
        {!frame ? (
          <button onClick={capture} disabled={!camOk || !!busy} className="flex h-[72px] w-[72px] items-center justify-center rounded-full border-4 border-white bg-forest text-white shadow-lg disabled:opacity-40" aria-label="Capture"><Camera size={28} /></button>
        ) : (
          <button onClick={() => { stopSpeaking(); setFrame(null); setResult(null); setTt(null); setErr(null); }} className="btn btn-primary"><RotateCcw size={18} /> New look</button>
        )}
        <label className="btn btn-ghost cursor-pointer">
          <ImageIcon size={18} /> Photo
          <input type="file" accept="image/*" className="hidden" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ""; }} />
        </label>
      </div>

      {err && <p className="rounded-2xl bg-red-50 p-3 text-sm text-danger">{err}</p>}

      {result && (
        <motion.section initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="card space-y-3 p-4">
          {result.found && result.species_id ? (
            <>
              <div className="flex items-baseline justify-between">
                <h2 className="text-2xl font-black">{result.species_name}</h2>
                <span className="text-xs italic text-muted">{result.scientific_name}</span>
              </div>
              <p className="text-[17px] leading-relaxed">{result.narration}</p>
              <p className="flex gap-2 rounded-2xl bg-amber-soft p-3 text-sm text-[#92400e]"><Lightbulb size={18} className="shrink-0" /> {result.fun_fact}</p>
              <div className="flex items-center justify-between text-xs font-bold">
                {result.source_url && <a href={result.source_url} target="_blank" rel="noreferrer" className="-my-2 inline-flex min-h-11 items-center gap-1 text-forest">Source: park page <ExternalLink size={12} /></a>}
                <button onClick={() => speak(`${result.narration} ${result.fun_fact}`, result.language)} className="-my-2 inline-flex min-h-11 items-center gap-1 px-2 text-muted"><Volume2 size={16} /> read again</button>
              </div>
              {tt && (
                <button onClick={share} className="btn btn-amber w-full"><Share2 size={18} /> Share before / after</button>
              )}
              <div className="grid grid-cols-3 gap-2 pt-1">
                {MODES.map(({ mode, label, Icon }) => (
                  <button key={mode} onClick={() => timeTravel(mode)} disabled={!!busy}
                          className={`flex flex-col items-center gap-1 rounded-2xl border-2 p-2 text-xs font-bold ${tt?.mode === mode ? "border-forest bg-forest-soft text-forest" : "border-line text-ink"} disabled:opacity-40`}>
                    <Icon size={22} />{label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <>
              <p className="text-sm">{result.narration}</p>
              {result.found && (
                <p className="text-xs text-muted">ParkLens only tells stories it can back with the park&apos;s own pages, so it won&apos;t guess about this one.</p>
              )}
            </>
          )}
        </motion.section>
      )}
    </div>
  );
}
