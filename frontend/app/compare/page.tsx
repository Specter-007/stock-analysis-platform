import ComparisonPageClient from "@/components/comparison/ComparisonPageClient";
import { Skeleton } from "@/components/ui/Skeleton";
import { Suspense } from "react";

export const metadata = {
  title: "Stock Comparison — Stock Analyst",
};

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-[1400px] px-4 sm:px-6 py-8"><Skeleton className="h-96 w-full" /></div>}>
      <ComparisonPageClient />
    </Suspense>
  );
}
