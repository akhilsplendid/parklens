"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", label: "Family", icon: "👨‍👩‍👧" },
  { href: "/plan", label: "Plan", icon: "📋" },
  { href: "/map", label: "Map", icon: "🗺️" },
  { href: "/lens", label: "Lens", icon: "📷" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="fixed bottom-0 inset-x-0 z-20 border-t border-neutral-200 bg-white/95 backdrop-blur dark:bg-neutral-900/95 dark:border-neutral-800">
      <ul className="mx-auto flex max-w-md justify-around py-2">
        {tabs.map((t) => (
          <li key={t.href}>
            <Link href={t.href} className={`flex flex-col items-center px-4 text-xs ${path === t.href ? "text-emerald-600 font-semibold" : "text-neutral-500"}`}>
              <span className="text-xl">{t.icon}</span>
              {t.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
