export type CustomerStatus = "active" | "inactive" | "at_risk";

export interface CustomerResponse {
  id: string;
  name: string;
  email: string;
  status: CustomerStatus;
  lifetime_value: string;
  created_at: string;
}

export interface CustomerCreatePayload {
  name: string;
  email: string;
  status?: CustomerStatus;
  lifetime_value?: string;
}

export type CustomerUpdatePayload = Partial<CustomerCreatePayload>;
