export interface Customer {
  id: number;
  name: string;
  email: string;
  shopify_store_url: string;
  business_name?: string;
  contact_person?: string;
  phone?: string;
  address?: string;
  is_active: boolean;
  webhook_enabled: boolean;
  auto_fulfillment: boolean;
  created_at: string;
  updated_at?: string;
  owner_id: number;
}

export interface CustomerCreate {
  name: string;
  email: string;
  shopify_store_url: string;
  shopify_access_token: string;
  printify_api_token: string;
  business_name?: string;
  contact_person?: string;
  phone?: string;
  address?: string;
  webhook_enabled?: boolean;
  auto_fulfillment?: boolean;
}

export interface CustomerUpdate extends Partial<CustomerCreate> {}
