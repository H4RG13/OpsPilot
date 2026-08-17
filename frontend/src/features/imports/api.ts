import { api } from "@/lib/api";
import type { ImportJobResponse, ImportType } from "@/types/imports";

export async function uploadImport(file: File, importType: ImportType): Promise<ImportJobResponse> {
  const formData = new FormData();
  formData.append("import_type", importType);
  formData.append("file", file);
  const { data } = await api.post<ImportJobResponse>("/imports/csv", formData);
  return data;
}

export async function getImportJob(id: string): Promise<ImportJobResponse> {
  const { data } = await api.get<ImportJobResponse>(`/imports/${id}`);
  return data;
}
