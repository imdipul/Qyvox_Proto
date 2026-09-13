import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Qyvox — Prove the fact. Keep the data.",
    template: "%s · Qyvox",
  },
  description:
    "A zero-knowledge identity engine that proves age eligibility without sending your birth year to a server.",
  applicationName: "Qyvox",
  openGraph: {
    type: "website",
    siteName: "Qyvox",
    title: "Qyvox — Prove the fact. Keep the data.",
    description: "Zero-knowledge identity assurance without collecting the sensitive fact behind the claim.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Qyvox — Prove the fact. Keep the data.",
    description: "Zero-knowledge identity assurance without collecting the sensitive fact behind the claim.",
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#160f14",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <div className="site-shell">
          <div className="scene-grid" aria-hidden="true" />
          <div className="scene-glow scene-glow-one" aria-hidden="true" />
          <div className="scene-glow scene-glow-two" aria-hidden="true" />
          <SiteHeader />
          {children}
          <SiteFooter />
        </div>
      </body>
    </html>
  );
}
