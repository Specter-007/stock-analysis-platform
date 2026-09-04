import { Suspense } from "react";
import PaperTradingPageClient from "@/components/paper-trading/PaperTradingPageClient";
import { Skeleton } from "@/components/ui/Skeleton";
import { RequireAuth } from "@/components/auth/RequireAuth";

export const metadata = {
  title: "Paper Trading — Stock Analyst",
};

export default function PaperTradingPage() {
  return (
    <RequireAuth>
      <Suspense fallback={<div className="mx-auto max-w-[1200px] px-4 sm:px-6 py-8"><Skeleton className="h-96 w-full" /></div>}>
        <PaperTradingPageClient />
      </Suspense>
    </RequireAuth>
  );
}
