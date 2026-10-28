import type { Metadata } from "next";
import "./globals.css";
import { display, mono, sans } from "@/lib/fonts";
import { FontGateScript } from "@/components/FontGateScript";

export const metadata: Metadata = {
  title: "Floor Plan — Video",
  description:
    "Turn a 2D floor plan into an architectural walkthrough video in under an hour.",
  icons: [{ rel: "icon", url: "/favicon.svg", type: "image/svg+xml" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${display.variable} ${mono.variable}`}>
      <head>
        <FontGateScript />
      </head>
      <body className="min-h-screen bg-paper text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
