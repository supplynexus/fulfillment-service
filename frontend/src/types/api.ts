// API response types
export interface ApiResponse<T = unknown> {
  success?: boolean;
  message?: string;
  data?: T;
  detail?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  details?: {
    shop_id?: string;
    shop_name?: string;
    access_token?: string;
    base_url?: string;
  };
}

export interface SyncResult {
  success: boolean;
  message: string;
  orders_synced?: number;
  orders_updated?: number;
  total_processed?: number;
  errors?: string[];
}

export interface ExternalSystem {
  id_hashid: string;
  name: string;
  system_type: string;
  external_id: string;
  base_url?: string;
  credentials?: {
    access_token?: string;
    shop_id?: string;
  };
  settings?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  title: string;
  handle: string;
  vendor?: string;
  product_type?: string;
  status: string;
  created_at: string;
  updated_at: string;
  variants?: Array<{
    id: string;
    title: string;
    price: string;
    sku?: string;
    inventory_quantity?: number;
  }>;
}

export interface Order {
  id: string;
  order_number?: string;
  email?: string;
  phone?: string;
  financial_status: string;
  fulfillment_status: string;
  total_price: string;
  currency: string;
  created_at: string;
  updated_at: string;
  shipping_address?: {
    first_name?: string;
    last_name?: string;
    address1?: string;
    city?: string;
    province?: string;
    country?: string;
    zip?: string;
  };
  billing_address?: {
    first_name?: string;
    last_name?: string;
    address1?: string;
    city?: string;
    province?: string;
    country?: string;
    zip?: string;
  };
  line_items?: Array<{
    id: string;
    title: string;
    quantity: number;
    price: string;
    variant_id?: string;
    product_id?: string;
  }>;
}
