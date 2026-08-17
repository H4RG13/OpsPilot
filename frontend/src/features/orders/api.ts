import { api } from "@/lib/api";
import type { Page } from "@/types/pagination";
import type { OrderCreatePayload, OrderResponse, OrderStatus } from "@/types/orders";

export interface OrderListParams {
  page?: number;
  page_size?: number;
  status?: OrderStatus;
}

export async function listOrders(params: OrderListParams): Promise<Page<OrderResponse>> {
  const { data } = await api.get<Page<OrderResponse>>("/orders", { params });
  return data;
}

export async function createOrder(payload: OrderCreatePayload): Promise<OrderResponse> {
  const { data } = await api.post<OrderResponse>("/orders", payload);
  return data;
}

export async function updateOrderStatus(id: string, status: OrderStatus): Promise<OrderResponse> {
  const { data } = await api.patch<OrderResponse>(`/orders/${id}`, { status });
  return data;
}
