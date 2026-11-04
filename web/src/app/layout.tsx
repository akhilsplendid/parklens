import type { Metadata, Viewport } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "ParkLens",
  description: "Your family's personal park guide: a day plan that fits your kids, and a camera that tells every animal's story.",
  manifest: "/manifest.json",
  icons: { icon: "/icon.svg", apple: "/apple-touch-icon.png" },
  appleWebApp: { capable: true, title: "ParkLens", statusBarStyle: "default" },
};
export const viewport: Viewport = { themeColor: "#0f5132", width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-full">
        <main className="mx-auto max-w-md px-4 pb-[calc(6.5rem+env(safe-area-inset-bottom))] pt-4">{children}</main>
        <Nav />
      </body>
    </html>
  );
}
