import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Only genuinely public, indexable pages - authenticated/private routes
// (settings, watchlist, paper-trading, experiments, research, onboarding)
// are deliberately excluded, matching app/robots.ts.
const PUBLIC_PATHS = [
  "",
  "/analysis",
  "/backtest",
  "/portfolio",
  "/compare",
  "/markets",
  "/model",
  "/docs",
  "/login",
  "/register",
  "/forgot-password",
  "/contact",
  "/terms",
  "/privacy",
  "/cookies",
  "/disclaimer",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PATHS.map((path) => ({
    url: `${SITE_URL}${path}`,
    lastModified: new Date(),
  }));
}
