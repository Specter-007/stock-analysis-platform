"use client";

import { getModelInfo } from "@/lib/api";
import { useApiResource } from "@/hooks/useApiResource";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonText } from "@/components/ui/Skeleton";
import type { ApiError } from "@/lib/api";

export default function ModelPageClient() {
  const { data, loading, error } = useApiResource((signal) => getModelInfo(signal), []);

  return (
    <div className="mx-auto max-w-[1100px] px-4 sm:px-6 py-8 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary mb-1">Model</h1>
        <p className="text-sm text-text-muted max-w-2xl">
          This page documents exactly how the signal is computed, so the model is auditable rather than a black
          box. Every number here is a fixed constant from the backend configuration - nothing is inferred.
        </p>
      </div>

      {error ? (
        <ErrorState error={error as ApiError} onRetry={() => window.location.reload()} />
      ) : loading || !data ? (
        <Card>
          <SkeletonText lines={8} />
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader title="Version" subtitle={`Current: Quant Model v${data.current_version}`} />
            <div className="flex flex-col gap-3">
              {data.supported_versions.map((v) => (
                <div key={v} className="border border-border rounded p-3 bg-bg-elevated">
                  <p className="text-sm font-medium text-text-primary mb-1">
                    v{v} {v === data.current_version && <span className="text-accent text-xs">(current)</span>}
                  </p>
                  <p className="text-xs text-text-muted leading-relaxed">{data.version_notes[v]}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Factor Weights" subtitle="Fixed point range each factor can contribute" />
            <div className="overflow-x-auto">
              <table className="w-full text-xs min-w-[500px]">
                <thead>
                  <tr className="text-left text-text-faint uppercase tracking-wide">
                    <th className="pb-2">Category</th>
                    <th className="pb-2">Factor</th>
                    <th className="pb-2 text-right">Min</th>
                    <th className="pb-2 text-right">Max</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.factor_weights.map((f, i) => (
                    <tr key={i}>
                      <td className="py-2 text-text-secondary">{f.category}</td>
                      <td className="py-2 text-text-primary">{f.factor}</td>
                      <td className="py-2 text-right tabular text-bearish">{f.min}</td>
                      <td className="py-2 text-right tabular text-bullish">+{f.max}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card>
            <CardHeader title="Score Thresholds" />
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {Object.entries(data.score_thresholds).map(([k, v]) => (
                <div key={k} className="border border-border rounded p-2.5 bg-bg-elevated">
                  <p className="text-text-faint uppercase tracking-wide text-[10px] mb-1">{k.replace(/_/g, " ")}</p>
                  <p className="text-text-primary font-medium tabular">{v}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Confidence Methodology" />
            <p className="text-xs text-text-secondary leading-relaxed">{data.confidence_methodology}</p>
          </Card>

          <Card>
            <CardHeader title="Risk Methodology" />
            <p className="text-xs text-text-secondary leading-relaxed">{data.risk_methodology}</p>
          </Card>

          <Card>
            <CardHeader title="Backtest Methodology" />
            <dl className="flex flex-col gap-3 text-xs">
              {Object.entries(data.backtest_methodology).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-text-secondary font-medium capitalize mb-0.5">{k.replace(/_/g, " ")}</dt>
                  <dd className="text-text-muted leading-relaxed">{v}</dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card>
            <CardHeader title="No-Look-Ahead-Bias Methodology" />
            <p className="text-xs text-text-secondary leading-relaxed">{data.no_look_ahead_methodology}</p>
          </Card>

          <Card>
            <CardHeader title="Data Limitations" />
            <ul className="flex flex-col gap-1.5">
              {data.data_limitations.map((l, i) => (
                <li key={i} className="text-xs text-text-secondary flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-text-faint mt-1.5 shrink-0" />
                  {l}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <p className="text-xs text-text-faint leading-relaxed">{data.disclaimer}</p>
          </Card>
        </>
      )}
    </div>
  );
}
