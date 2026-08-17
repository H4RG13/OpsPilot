import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { QueryState } from "@/components/common/QueryState";
import { Pagination } from "@/components/common/Pagination";
import { ReportDetailModal } from "@/features/reports/ReportDetailModal";
import { generateReport, listReports } from "@/features/reports/api";
import { getErrorMessage } from "@/lib/errors";
import { formatCurrency } from "@/lib/format";
import type { ReportResponse, ReportStatus } from "@/types/reports";

const STATUS_STYLES: Record<ReportStatus, string> = {
  queued: "bg-slate-700 text-slate-300",
  running: "bg-indigo-500/15 text-indigo-300",
  completed: "bg-emerald-500/15 text-emerald-300",
  failed: "bg-red-500/15 text-red-300",
};

const PAGE_SIZE = 20;

export function ReportsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [viewing, setViewing] = useState<ReportResponse | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["reports", { page }],
    queryFn: () => listReports({ page, page_size: PAGE_SIZE }),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasPending = items.some((r) => r.status === "queued" || r.status === "running");
      return hasPending ? 3000 : false;
    },
  });

  const generateMutation = useMutation({
    mutationFn: generateReport,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Reports</h1>
          <p className="mt-1 text-sm text-slate-400">
            AI-generated weekly performance summaries.
          </p>
        </div>
        <Button onClick={() => generateMutation.mutate()} isLoading={generateMutation.isPending}>
          Generate Report
        </Button>
      </div>

      {generateMutation.isError && (
        <Alert variant="error">{getErrorMessage(generateMutation.error)}</Alert>
      )}

      <Card>
        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No reports yet. Generate one to get started."
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2">Period</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Revenue</th>
                <th className="pb-2">Orders</th>
                <th className="pb-2">Growth</th>
                <th className="pb-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {data?.items.map((report) => (
                <tr key={report.id}>
                  <td className="py-2 text-slate-200">
                    {new Date(report.period_start).toLocaleDateString()} –{" "}
                    {new Date(report.period_end).toLocaleDateString()}
                  </td>
                  <td className="py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[report.status]}`}
                    >
                      {report.status}
                    </span>
                  </td>
                  <td className="py-2 text-slate-400">
                    {report.revenue ? formatCurrency(report.revenue) : "—"}
                  </td>
                  <td className="py-2 text-slate-400">{report.order_count ?? "—"}</td>
                  <td className="py-2 text-slate-400">
                    {report.growth_pct ? `${Number(report.growth_pct).toFixed(1)}%` : "—"}
                  </td>
                  <td className="py-2 text-right">
                    {(report.status === "completed" || report.status === "failed") && (
                      <button
                        className="text-xs text-indigo-400 hover:text-indigo-300"
                        onClick={() => setViewing(report)}
                      >
                        View
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>

        {data && (
          <div className="mt-4">
            <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
          </div>
        )}
      </Card>

      {viewing && <ReportDetailModal report={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}
