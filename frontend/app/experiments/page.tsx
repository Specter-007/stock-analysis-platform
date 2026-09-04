import ExperimentLabPageClient from "@/components/experiments/ExperimentLabPageClient";
import { RequireAuth } from "@/components/auth/RequireAuth";

export const metadata = {
  title: "Experiment Lab — Stock Analyst",
};

export default function ExperimentsPage() {
  return (
    <RequireAuth>
      <ExperimentLabPageClient />
    </RequireAuth>
  );
}
