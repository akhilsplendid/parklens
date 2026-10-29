"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Users, ListChecks, Map, Camera } from "lucide-react";

const tabs = [
  { href: "/", label: "Family", Icon: Users },
  { href: "/plan", label: "Plan", Icon: ListChecks },
  { href: "/map", label: "Map", Icon: Map },
  { href: "/lens", label: "Lens", Icon: Camera },
];

export default function Nav() {
  const path = usePathname();
  if (path === "/welcome") return null;
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-surface/95 backdrop-blur" style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
      <ul className="mx-auto flex max-w-md justify-around py-1.5">
        {tabs.map(({ href, label, Icon }) => {
          const active = path === href;
          return (
            <li key={href}>
              <Link href={href} className={`flex min-w-[64px] flex-col items-center gap-0.5 rounded-xl px-3 py-1.5 text-[11px] font-extrabold ${active ? "text-forest" : "text-muted"}`}>
                <span className={`rounded-full px-3 py-1 ${active ? "bg-forest-soft" : ""}`}><Icon size={22} strokeWidth={active ? 2.5 : 2} /></span>
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
