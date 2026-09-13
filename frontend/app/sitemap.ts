import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return ["", "/whitepaper", "/docs", "/research", "/faq"].map((path) => ({
    url: `${baseUrl}${path}`,
    lastModified: new Date("2026-08-26T00:00:00Z"),
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : 0.8,
  }));
}
