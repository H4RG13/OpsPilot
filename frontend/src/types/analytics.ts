export interface OverviewResponse {
  start_date: string;
  end_date: string;
  revenue: string;
  order_count: number;
  average_order_value: string;
  total_customers: number;
  active_customers: number;
}

export interface RevenuePoint {
  period_start: string;
  revenue: string;
  order_count: number;
}

export type RevenueGranularity = "day" | "week" | "month";

export interface RevenueTrendResponse {
  start_date: string;
  end_date: string;
  granularity: RevenueGranularity;
  points: RevenuePoint[];
}

export interface TopProductItem {
  product_id: string;
  name: string;
  category: string;
  revenue: string;
  quantity_sold: number;
}

export interface ProductsPerformanceResponse {
  start_date: string;
  end_date: string;
  products: TopProductItem[];
}

export interface CustomerMetricsResponse {
  start_date: string;
  end_date: string;
  total_customers: number;
  new_customers: number;
  active_customers: number;
  at_risk_customers: number;
}
