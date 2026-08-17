export type ImportType = "customers" | "products";
export type ImportStatus = "queued" | "running" | "completed" | "failed";

export interface ImportRowError {
  row: number;
  message: string;
}

export interface ImportJobResponse {
  id: string;
  import_type: ImportType;
  status: ImportStatus;
  filename: string;
  total_rows: number | null;
  imported_rows: number | null;
  failed_rows: number | null;
  errors: ImportRowError[];
  created_at: string;
  completed_at: string | null;
}

export const REQUIRED_COLUMNS: Record<ImportType, string[]> = {
  customers: ["name", "email"],
  products: ["name", "category", "price"],
};
