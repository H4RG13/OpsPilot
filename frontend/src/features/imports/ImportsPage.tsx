import { useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Alert } from "@/components/ui/Alert";
import { ImportJobCard } from "@/features/imports/ImportJobCard";
import { uploadImport } from "@/features/imports/api";
import { useAuth } from "@/features/auth/AuthContext";
import { canWrite } from "@/lib/permissions";
import { getErrorMessage } from "@/lib/errors";
import { REQUIRED_COLUMNS } from "@/types/imports";
import type { ImportJobResponse, ImportType } from "@/types/imports";

export function ImportsPage() {
  const { me } = useAuth();
  const canImport = canWrite(me?.role);

  const [importType, setImportType] = useState<ImportType>("customers");
  const [jobs, setJobs] = useState<ImportJobResponse[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadImport(file, importType),
    onSuccess: (job) => {
      setJobs((prev) => [job, ...prev]);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
  });

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) uploadMutation.mutate(file);
  }

  if (!canImport) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold text-slate-100">Imports</h1>
        <Alert variant="info">Only organization admins and owners can import data.</Alert>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Imports</h1>
        <p className="mt-1 text-sm text-slate-400">Bulk-import customers or products from CSV.</p>
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <Select
            label="Import type"
            value={importType}
            onChange={(e) => setImportType(e.target.value as ImportType)}
            className="max-w-xs"
          >
            <option value="customers">Customers</option>
            <option value="products">Products</option>
          </Select>
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-slate-300">CSV file</span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              disabled={uploadMutation.isPending}
              className="text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:py-2 file:text-sm file:text-slate-100 hover:file:bg-slate-700"
            />
          </div>
          {uploadMutation.isPending && <span className="text-sm text-slate-500">Uploading…</span>}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Required columns for <span className="capitalize">{importType}</span>:{" "}
          {REQUIRED_COLUMNS[importType].join(", ")}
        </p>
        {uploadMutation.isError && (
          <div className="mt-3">
            <Alert variant="error">{getErrorMessage(uploadMutation.error)}</Alert>
          </div>
        )}
      </Card>

      {jobs.length === 0 ? (
        <p className="text-sm text-slate-500">No imports uploaded this session yet.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {jobs.map((job) => (
            <ImportJobCard key={job.id} initialJob={job} />
          ))}
        </div>
      )}
    </div>
  );
}
