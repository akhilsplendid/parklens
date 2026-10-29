"use client";
import { useRef, useState } from "react";
import { Mic } from "lucide-react";

// Hold-to-talk microphone button. Returns a webm/opus blob when released.
export default function Recorder({ onAudio, disabled }: { onAudio: (b: Blob) => void; disabled?: boolean }) {
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const [rec_, setRec] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      const r = new MediaRecorder(stream, { mimeType: mime });
      chunks.current = [];
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      r.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        onAudio(new Blob(chunks.current, { type: "audio/webm" }));
      };
      r.start();
      rec.current = r;
      setRec(true);
      setErr(null);
    } catch {
      setErr("Microphone not available. Use HTTPS or type instead.");
    }
  }
  function stop() {
    if (rec.current?.state === "recording") rec.current.stop();
    setRec(false);
  }
  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        disabled={disabled}
        onPointerDown={start}
        onPointerUp={stop}
        onPointerLeave={stop}
        className={`flex h-20 w-20 items-center justify-center rounded-full shadow-lg transition ${rec_ ? "scale-110 bg-danger" : "bg-forest"} text-white disabled:opacity-40`}
        aria-label="Hold to talk"
      >
        <Mic size={32} />
      </button>
      <span className="text-xs font-bold text-muted">{rec_ ? "Listening… release to send" : "Hold to talk"}</span>
      {err && <span className="text-xs text-danger">{err}</span>}
    </div>
  );
}
