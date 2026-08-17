import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { getImportJob } from "@/features/imports/api";
import type { ImportJobResponse, ImportStatus } from "@/types/imports";

const STATUS_STYLES: Record<ImportStatus, string> = {
  queued: "bg-slate-700 text-slate-300",
  running: "bg-indigo-500/15 text-indigo-300",
  completed: "bg-emerald-500/15 text-emerald-300",
  failed: "bg-red-500/15 text-red-300",
};

export function ImportJobCard({ initialJob }: { initialJob: ImportJobResponse }) {
  const { data: job } = useQuery({
    queryKey: ["imports", initialJob.id],
    queryFn: () => getImportJob(initialJob.id),
    initialData: initialJob,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 2000 : false;
    },
  });

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-200">{job.filename}</p>
          <p className="text-xs text-slate-500 capitalize">{job.import_type}</p>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[job.status]}`}>
          {job.status}
        </span>
      </div>

      {(job.status === "completed" || job.status === "failed") && (
        <div className="mt-3 flex gap-4 text-sm text-slate-400">
          <span>Total: {job.total_rows ?? "—"}</span>
          <span className="text-emerald-400">Imported: {job.imported_rows ?? "—"}</span>
          <span className="text-red-400">Failed: {job.failed_rows ?? "—"}</span>
        </div>
      )}

      {job.errors.length > 0 && (
        <div className="mt-3 max-h-40 overflow-auto rounded-md border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500">
                <th className="px-2 py-1">Row</th>
                <th className="px-2 py-1">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {job.errors.map((err, index) => (
                <tr key={index}>
                  <td className="px-2 py-1 text-slate-400">{err.row || "—"}</td>
                  <td className="px-2 py-1 text-red-400">{err.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
