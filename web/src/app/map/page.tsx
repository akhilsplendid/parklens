"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, saveStored, useStored, type KbItem, type ParkMap, type Plan } from "@/lib/api";

// A schematic park map drawn from the GPS points on the park's own pages: every located
// animal and ride, the planned route in order, and an "I'm here" marker for demo mode.
export default function MapPage() {
  const plan = useStored<Plan>("plan");
  const here = useStored<string>("here");
  const [items, setItems] = useState<KbItem[]>([]);
  const [map, setMap] = useState<ParkMap | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.items(), api.map()]).then(([i, m]) => { setItems(i); setMap(m); }).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p className="text-red-700">{err}</p>;
  if (!map?.bounds) return <p className="text-muted">Loading map…</p>;

  const W = 1000, H = 420, pad = 40;
  const b = map.bounds;
  const x = (lon: number) => pad + ((lon - b.min_lon) / (b.max_lon - b.min_lon)) * (W - 2 * pad);
  const y = (lat: number) => pad + ((b.max_lat - lat) / (b.max_lat - b.min_lat)) * (H - 2 * pad);
  const located = items.filter((i) => i.lat != null && i.lon != null);
  const route = (plan?.stops ?? []).filter((s) => s.lat != null && s.lon != null);
  const routeIds = new Set(route.map((s) => s.item_id));
  const hereItem = located.find((i) => i.id === here);

  return (
    <div className="space-y-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-2xl font-black">{map.park}</h1>
        <span className="text-xs text-muted">{located.length} places · from the park&apos;s own pages</span>
      </header>

      <div className="overflow-hidden rounded-2xl bg-[#0f2a1c] ring-1 ring-forest/30">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Park map">
          <defs>
            <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M50 0H0V50" fill="none" stroke="#14532d" strokeOpacity="0.35" />
            </pattern>
          </defs>
          <rect width={W} height={H} fill="url(#grid)" />
          {/* route */}
          {route.length > 1 && (
            <polyline
              points={[`${x(map.entrance.lon)},${y(map.entrance.lat)}`, ...route.map((s) => `${x(s.lon!)},${y(s.lat!)}`)].join(" ")}
              fill="none" stroke="#34d399" strokeWidth="4" strokeDasharray="10 8" strokeLinejoin="round"
            />
          )}
          {/* all places */}
          {located.map((i) => (
            <g key={i.id} onClick={() => saveStored("here", i.id)} className="cursor-pointer">
              <circle cx={x(i.lon!)} cy={y(i.lat!)} r={routeIds.has(i.id) ? 11 : 7}
                      fill={i.kind === "attraction" ? "#f59e0b" : "#60a5fa"} fillOpacity={routeIds.has(i.id) ? 1 : 0.45}
                      stroke={here === i.id ? "#fff" : "none"} strokeWidth="3" />
              <title>{i.name}</title>
            </g>
          ))}
          {/* route numbers */}
          {route.map((s, n) => (
            <text key={`${s.item_id}-n`} x={x(s.lon!)} y={y(s.lat!) + 4} textAnchor="middle" fontSize="12" fontWeight="700" fill="#052e16">{n + 1}</text>
          ))}
          {/* entrance */}
          <g>
            <rect x={x(map.entrance.lon) - 9} y={y(map.entrance.lat) - 9} width="18" height="18" rx="3" fill="#fff" />
            <text x={x(map.entrance.lon)} y={y(map.entrance.lat) + 4} textAnchor="middle" fontSize="12" fontWeight="700" fill="#052e16">E</text>
          </g>
          {/* here */}
          {hereItem && (
            <text x={x(hereItem.lon!)} y={y(hereItem.lat!) - 16} textAnchor="middle" fontSize="13" fontWeight="700" fill="#fff">📍 you</text>
          )}
        </svg>
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-muted">
        <span><span className="inline-block h-3 w-3 rounded-full bg-blue-400 align-middle" /> animal</span>
        <span><span className="inline-block h-3 w-3 rounded-full bg-amber-500 align-middle" /> ride</span>
        <span><span className="inline-block h-3 w-3 rounded-sm bg-white align-middle" /> entrance</span>
        <span className="text-emerald-400">- - - today&apos;s route</span>
      </div>

      {plan ? (
        <ol className="grid grid-cols-2 gap-1.5 text-sm">
          {route.map((s, n) => (
            <li key={s.item_id} className={`card px-2 py-1.5 ${here === s.item_id ? "ring-2 ring-forest" : ""}`}>
              <button onClick={() => saveStored("here", s.item_id)} className="text-left">
                <span className="mr-1 font-mono text-muted">{n + 1}</span>{s.name}
                {s.walk_minutes ? <span className="ml-1 text-muted">· {s.walk_minutes} min</span> : null}
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-sm text-muted">No plan yet. <Link href="/" className="underline">Set up your family</Link> and the route appears here.</p>
      )}

      <p className="text-xs text-muted">
        Tap a place to mark where you are (demo mode). The Lens then uses that as a hint.
        {here && <button onClick={() => saveStored("here", "")} className="ml-2 underline">clear</button>}
      </p>
    </div>
  );
}
