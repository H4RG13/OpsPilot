import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { QueryState } from "@/components/common/QueryState";
import { getCustomerMetrics } from "@/features/dashboard/api";

function Metric({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className={`text-lg font-semibold ${highlight ? "text-amber-400" : "text-slate-100"}`}>
        {value.toLocaleString()}
      </dd>
    </div>
  );
}

export function CustomerActivityCard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["analytics", "customers"],
    queryFn: getCustomerMetrics,
  });

  return (
    <Card>
      <h2 className="text-sm font-semibold text-slate-200">Customer Activity</h2>
      <div className="mt-4">
        <QueryState isLoading={isLoading} isError={isError} error={error}>
          {data && (
            <dl className="grid grid-cols-2 gap-4">
              <Metric label="Total" value={data.total_customers} />
              <Metric label="New (30d)" value={data.new_customers} />
              <Metric label="Active (30d)" value={data.active_customers} />
              <Metric
                label="At Risk"
                value={data.at_risk_customers}
                highlight={data.at_risk_customers > 0}
              />
            </dl>
          )}
        </QueryState>
      </div>
    </Card>
  );
}
