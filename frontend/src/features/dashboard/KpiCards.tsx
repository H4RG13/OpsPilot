import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { QueryState } from "@/components/common/QueryState";
import { getOverview } from "@/features/dashboard/api";
import { formatCurrency } from "@/lib/format";

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-100">{value}</p>
    </Card>
  );
}

function KpiSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }, (_, i) => (
        <Card key={i} className="animate-pulse">
          <div className="h-3 w-1/2 rounded bg-slate-800" />
          <div className="mt-3 h-7 w-2/3 rounded bg-slate-800" />
        </Card>
      ))}
    </div>
  );
}

export function KpiCards() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: getOverview,
  });

  return (
    <QueryState isLoading={isLoading} isError={isError} error={error} loadingFallback={<KpiSkeleton />}>
      {data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Revenue (30d)" value={formatCurrency(data.revenue)} />
          <KpiCard label="Orders" value={data.order_count.toLocaleString()} />
          <KpiCard label="Active Customers" value={data.active_customers.toLocaleString()} />
          <KpiCard label="Avg. Order Value" value={formatCurrency(data.average_order_value)} />
        </div>
      )}
    </QueryState>
  );
}
