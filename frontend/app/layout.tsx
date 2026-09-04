import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import TopNav from "@/components/nav/TopNav";
import SiteFooter from "@/components/nav/SiteFooter";
import { AuthProvider } from "@/lib/auth-context";
import { CookieConsentBanner } from "@/components/legal/CookieConsentBanner";
import { SITE_URL } from "@/lib/site";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Stock Analyst — Quantitative Research Terminal",
  description:
    "Deterministic, rules-based stock research and technical analysis, powered by real Yahoo Finance market data. Not a financial adviser.",
  openGraph: {
    title: "Stock Analyst — Quantitative Research Terminal",
    description:
      "Deterministic, rules-based stock research and technical analysis, powered by real Yahoo Finance market data. Not a financial adviser.",
    url: SITE_URL,
    siteName: "Stock Analyst",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-bg text-text-primary antialiased">
        <AuthProvider>
          <TopNav />
          <main className="flex-1 w-full">{children}</main>
          <SiteFooter />
          <CookieConsentBanner />
        </AuthProvider>
      </body>
    </html>
  );
}
