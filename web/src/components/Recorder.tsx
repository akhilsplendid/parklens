"use client";
import { useRef, useState } from "react";
import { Mic } from "lucide-react";
import { unlockSpeech } from "@/lib/api";

// Hold-to-talk microphone button. Returns an audio blob (webm/opus on Chrome, mp4/aac on
// iOS Safari) when released. The blob's `type` tells the API which container it is.
export default function Recorder({ onAudio, disabled }: { onAudio: (b: Blob) => void; disabled?: boolean }) {
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const held = useRef(false); // still pressed? (the permission prompt can outlast a tap)
  const [rec_, setRec] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function start() {
    held.current = true;
    unlockSpeech(); // a user gesture: lets iOS speak the answer later
    if (rec.current) return;
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") throw new Error("unsupported");
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!held.current) { stream.getTracks().forEach((t) => t.stop()); return; } // released while asking
      const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"].find((m) => MediaRecorder.isTypeSupported(m));
      const r = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      r.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        rec.current = null;
        const type = (r.mimeType || mime || "audio/webm").split(";")[0];
        const blob = new Blob(chunks.current, { type });
        if (blob.size > 0) onAudio(blob);
      };
      r.start();
      rec.current = r;
      setRec(true);
      setErr(null);
      if (!held.current) stop(); // released during start()
    } catch (e) {
      const name = (e as Error)?.name;
      setErr(
        name === "NotAllowedError"
          ? "Microphone permission denied. Allow it in your browser settings, or type instead."
          : "Microphone not available here. Type instead.",
      );
    }
  }
  function stop() {
    held.current = false;
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
        onPointerCancel={stop}
        onContextMenu={(e) => e.preventDefault()}
        style={{ touchAction: "none", WebkitUserSelect: "none", WebkitTouchCallout: "none" }}
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
