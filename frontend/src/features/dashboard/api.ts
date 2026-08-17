import { api } from "@/lib/api";
import type {
  CustomerMetricsResponse,
  OverviewResponse,
  ProductsPerformanceResponse,
  RevenueGranularity,
  RevenueTrendResponse,
} from "@/types/analytics";
import type { Page } from "@/types/pagination";
import type { OrderResponse } from "@/types/orders";
import type { TaskResponse } from "@/types/tasks";

export async function getOverview(): Promise<OverviewResponse> {
  const { data } = await api.get<OverviewResponse>("/analytics/overview");
  return data;
}

export async function getRevenueTrend(
  granularity: RevenueGranularity
): Promise<RevenueTrendResponse> {
  const { data } = await api.get<RevenueTrendResponse>("/analytics/revenue", {
    params: { granularity },
  });
  return data;
}

export async function getTopProducts(limit = 5): Promise<ProductsPerformanceResponse> {
  const { data } = await api.get<ProductsPerformanceResponse>("/analytics/products", {
    params: { limit },
  });
  return data;
}

export async function getCustomerMetrics(): Promise<CustomerMetricsResponse> {
  const { data } = await api.get<CustomerMetricsResponse>("/analytics/customers");
  return data;
}

export async function getRecentOrders(limit = 5): Promise<Page<OrderResponse>> {
  const { data } = await api.get<Page<OrderResponse>>("/orders", {
    params: { page: 1, page_size: limit },
  });
  return data;
}

export async function getRecentTasks(limit = 5): Promise<Page<TaskResponse>> {
  const { data } = await api.get<Page<TaskResponse>>("/tasks", {
    params: { page: 1, page_size: limit },
  });
  return data;
}
