export interface ProductResponse {
  id: string;
  name: string;
  category: string;
  price: string;
  active: boolean;
  created_at: string;
}

export interface ProductCreatePayload {
  name: string;
  category: string;
  price: string;
  active?: boolean;
}

export type ProductUpdatePayload = Partial<ProductCreatePayload>;
