export type OrderStatus = "pending" | "completed" | "cancelled";

export interface OrderItemResponse {
  id: string;
  product_id: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
}

export interface OrderResponse {
  id: string;
  customer_id: string;
  status: OrderStatus;
  total_amount: string;
  ordered_at: string;
  items: OrderItemResponse[];
}

export interface OrderItemInput {
  product_id: string;
  quantity: number;
}

export interface OrderCreatePayload {
  customer_id: string;
  items: OrderItemInput[];
}

