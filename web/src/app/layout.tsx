import type { Metadata, Viewport } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "ParkLens",
  description: "Your family's personal park guide: a day plan that fits your kids, and a camera that tells every animal's story.",
  manifest: "/manifest.json",
  appleWebApp: { capable: true, title: "ParkLens", statusBarStyle: "black-translucent" },
};
export const viewport: Viewport = { themeColor: "#059669", width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
        <main className="mx-auto max-w-md px-4 pb-24 pt-4">{children}</main>
        <Nav />
      </body>
    </html>
  );
}
