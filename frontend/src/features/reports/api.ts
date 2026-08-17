import { api } from "@/lib/api";
import type { Page } from "@/types/pagination";
import type { ReportResponse } from "@/types/reports";

export interface ReportListParams {
  page?: number;
  page_size?: number;
}

export async function listReports(params: ReportListParams): Promise<Page<ReportResponse>> {
  const { data } = await api.get<Page<ReportResponse>>("/reports", { params });
  return data;
}

export async function generateReport(): Promise<ReportResponse> {
  const { data } = await api.post<ReportResponse>("/reports/generate");
  return data;
}
