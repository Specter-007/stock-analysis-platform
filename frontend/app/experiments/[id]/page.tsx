import ExperimentDetailPageClient from "@/components/experiments/ExperimentDetailPageClient";
import { RequireAuth } from "@/components/auth/RequireAuth";

export const metadata = {
  title: "Experiment — Stock Analyst",
};

export default async function ExperimentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <RequireAuth>
      <ExperimentDetailPageClient id={id} />
    </RequireAuth>
  );
}
