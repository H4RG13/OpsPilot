import { api } from "@/lib/api";
import type { Page } from "@/types/pagination";
import type { ProductCreatePayload, ProductResponse, ProductUpdatePayload } from "@/types/products";

export interface ProductListParams {
  page?: number;
  page_size?: number;
  category?: string;
  active?: boolean;
}

export async function listProducts(params: ProductListParams): Promise<Page<ProductResponse>> {
  const { data } = await api.get<Page<ProductResponse>>("/products", { params });
  return data;
}

export async function createProduct(payload: ProductCreatePayload): Promise<ProductResponse> {
  const { data } = await api.post<ProductResponse>("/products", payload);
  return data;
}

export async function updateProduct(
  id: string,
  payload: ProductUpdatePayload
): Promise<ProductResponse> {
  const { data } = await api.patch<ProductResponse>(`/products/${id}`, payload);
  return data;
}

export async function deleteProduct(id: string): Promise<void> {
  await api.delete(`/products/${id}`);
}
