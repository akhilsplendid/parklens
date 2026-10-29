"use client";
import { useState } from "react";

// Illustration with a graceful fallback (a soft gradient block) if the asset is missing.
// Illustrations live in /public/art/<name>.webp; "icon" is the app icon (SVG).
export default function Art({ name, alt, className = "" }: { name: string; alt: string; className?: string }) {
  const [ok, setOk] = useState(true);
  if (!ok) return <div className={`rounded-2xl bg-gradient-to-br from-forest-soft to-amber-soft ${className}`} aria-hidden />;
  const src = name === "icon" ? "/icon.svg" : `/art/${name}.webp`;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} onError={() => setOk(false)} className={`rounded-2xl object-cover ${className}`} />;
}
