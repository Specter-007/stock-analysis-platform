import ExperimentDetailPageClient from "@/components/experiments/ExperimentDetailPageClient";

export const metadata = {
  title: "Experiment — Stock Analyst",
};

export default async function ExperimentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ExperimentDetailPageClient id={id} />;
}
