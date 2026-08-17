import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui/Card";
import { QueryState } from "@/components/common/QueryState";
import { getRevenueTrend } from "@/features/dashboard/api";
import type { RevenueGranularity } from "@/types/analytics";

const GRANULARITIES: RevenueGranularity[] = ["day", "week", "month"];

export function RevenueChart() {
  const [granularity, setGranularity] = useState<RevenueGranularity>("day");
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["analytics", "revenue", granularity],
    queryFn: () => getRevenueTrend(granularity),
  });

  const chartData =
    data?.points.map((point) => ({
      date: point.period_start,
      revenue: Number(point.revenue),
    })) ?? [];

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Revenue Trend</h2>
        <div className="flex gap-1">
          {GRANULARITIES.map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setGranularity(g)}
              className={`rounded px-2 py-1 text-xs capitalize transition-colors ${
                granularity === g
                  ? "bg-indigo-500/20 text-indigo-300"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 h-64">
        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && chartData.length === 0}
          emptyMessage="No revenue recorded in this range yet."
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
                labelStyle={{ color: "#cbd5e1" }}
                formatter={(value: number) => [`$${value.toFixed(2)}`, "Revenue"]}
              />
              <Area type="monotone" dataKey="revenue" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </QueryState>
      </div>
    </Card>
  );
}
