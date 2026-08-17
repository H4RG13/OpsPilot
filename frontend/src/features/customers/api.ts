import { api } from "@/lib/api";
import type { Page } from "@/types/pagination";
import type {
  CustomerCreatePayload,
  CustomerResponse,
  CustomerStatus,
  CustomerUpdatePayload,
} from "@/types/customers";

export interface CustomerListParams {
  page?: number;
  page_size?: number;
  search?: string;
  status?: CustomerStatus;
}

export async function listCustomers(params: CustomerListParams): Promise<Page<CustomerResponse>> {
  const { data } = await api.get<Page<CustomerResponse>>("/customers", { params });
  return data;
}

export async function createCustomer(payload: CustomerCreatePayload): Promise<CustomerResponse> {
  const { data } = await api.post<CustomerResponse>("/customers", payload);
  return data;
}

export async function updateCustomer(
  id: string,
  payload: CustomerUpdatePayload
): Promise<CustomerResponse> {
  const { data } = await api.patch<CustomerResponse>(`/customers/${id}`, payload);
  return data;
}

export async function deleteCustomer(id: string): Promise<void> {
  await api.delete(`/customers/${id}`);
}
