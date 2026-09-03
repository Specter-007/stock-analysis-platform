import { Suspense } from "react";
import AnalysisPageClient from "@/components/stock/AnalysisPageClient";
import { Skeleton } from "@/components/ui/Skeleton";

export const metadata = {
  title: "Stock Analysis — Stock Analyst",
};

export default function AnalysisPage() {
  return (
    <Suspense fallback={<AnalysisFallback />}>
      <AnalysisPageClient />
    </Suspense>
  );
}

function AnalysisFallback() {
  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-[420px] w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}
