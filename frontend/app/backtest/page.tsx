import { Suspense } from "react";
import BacktestPageClient from "@/components/backtest/BacktestPageClient";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata = {
  title: "Backtesting — Stock Analyst",
};

export default function BacktestPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8"><Skeleton className="h-96 w-full" /></div>}>
      <BacktestPageClient />
    </Suspense>
  );
}
