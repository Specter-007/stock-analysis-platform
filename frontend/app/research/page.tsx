import ResearchHistoryPageClient from "@/components/research/ResearchHistoryPageClient";
import { RequireAuth } from "@/components/auth/RequireAuth";

export const metadata = {
  title: "Research History — Stock Analyst",
};

export default function ResearchPage() {
  return (
    <RequireAuth>
      <ResearchHistoryPageClient />
    </RequireAuth>
  );
}
