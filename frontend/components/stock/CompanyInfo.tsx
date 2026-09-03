import type { OverviewData } from "@/types/api";
import { Card, CardHeader } from "@/components/ui/Card";

export function CompanyInfo({ data }: { data: OverviewData }) {
  return (
    <Card>
      <CardHeader title="Company Information" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs mb-4">
        <Field label="Sector" value={data.sector} />
        <Field label="Industry" value={data.industry} />
        <Field label="Exchange" value={data.exchange} />
        <Field
          label="Website"
          value={data.website}
          href={data.website !== "N/A" ? data.website : undefined}
        />
      </div>
      {data.description !== "N/A" && (
        <p className="text-xs text-text-secondary leading-relaxed">{data.description}</p>
      )}
    </Card>
  );
}

function Field({ label, value, href }: { label: string; value: string; href?: string }) {
  return (
    <div>
      <p className="text-text-faint uppercase text-[10px] tracking-wide mb-1">{label}</p>
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:underline truncate block"
        >
          {value}
        </a>
      ) : (
        <p className="text-text-primary truncate">{value}</p>
      )}
    </div>
  );
}
