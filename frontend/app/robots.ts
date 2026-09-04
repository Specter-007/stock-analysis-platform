import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Authenticated/private pages, and anything that carries a one-time
      // token in its query string - none of this is meaningful to index,
      // and a crawled/cached token URL is worth avoiding even though the
      // tokens are single-use.
      disallow: [
        "/settings",
        "/watchlist",
        "/paper-trading",
        "/experiments",
        "/research",
        "/onboarding",
        "/reset-password",
        "/verify-email",
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
