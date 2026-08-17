export type ReportStatus = "queued" | "running" | "completed" | "failed";

export interface ReportResponse {
  id: string;
  period_start: string;
  period_end: string;
  status: ReportStatus;
  revenue: string | null;
  order_count: number | null;
  growth_pct: string | null;
  summary: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}
