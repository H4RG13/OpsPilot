import type { ReactNode } from "react";
import { Alert } from "@/components/ui/Alert";
import { getErrorMessage } from "@/lib/errors";

interface QueryStateProps {
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  isEmpty?: boolean;
  emptyMessage?: string;
  loadingFallback?: ReactNode;
  children: ReactNode;
}

function DefaultSkeleton() {
  return (
    <div className="animate-pulse space-y-2">
      <div className="h-4 w-2/3 rounded bg-slate-800" />
      <div className="h-4 w-1/2 rounded bg-slate-800" />
    </div>
  );
}

/** Every dashboard widget renders through this so loading/error/empty states
 * stay consistent across the page (spec Section 15 requires all three,
 * explicitly, for every widget). */
export function QueryState({
  isLoading,
  isError,
  error,
  isEmpty,
  emptyMessage = "No data yet.",
  loadingFallback,
  children,
}: QueryStateProps) {
  if (isLoading) return <>{loadingFallback ?? <DefaultSkeleton />}</>;
  if (isError) return <Alert variant="error">{getErrorMessage(error)}</Alert>;
  if (isEmpty) return <p className="text-sm text-slate-500">{emptyMessage}</p>;
  return <>{children}</>;
}
