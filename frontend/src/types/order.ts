export interface Order {
  id: number;
  shopify_order_id?: string;
  external_order_id?: string;
  external_order_name?: string;
  external_order_number?: string;
  shopify_order_number?: string;
  shopify_order_name?: string;
  printify_order_id?: string;
  status: OrderStatus;
  total_amount: number;
  currency: string;
  customer_email: string;
  customer_name?: string;
  customer_phone?: string;
  shipping_address: ShippingAddress;
  billing_address?: BillingAddress;
  line_items: LineItem[];
  error_message?: string;
  retry_count: number;
  last_retry_at?: string;
  tracking_number?: string;
  tracking_url?: string;
  fulfillment_status?: string;
  order_date: string;
  processed_at?: string;
  fulfilled_at?: string;
  created_at: string;
  updated_at?: string;
  customer_id?: number;
}

export interface OrderCreate {
  shopify_order_id: string;
  shopify_order_number?: string;
  shopify_order_name?: string;
  total_amount: number;
  currency?: string;
  customer_email: string;
  customer_name?: string;
  customer_phone?: string;
  shipping_address: ShippingAddress;
  billing_address?: BillingAddress;
  line_items: LineItem[];
  order_date: string;
  customer_id: number;
}

export enum OrderStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  FULFILLED = 'fulfilled',
  CANCELLED = 'cancelled',
  FAILED = 'failed',
  REFUNDED = 'refunded',
}

export interface ShippingAddress {
  first_name: string;
  last_name: string;
  company?: string;
  address1: string;
  address2?: string;
  city: string;
  province: string;
  country: string;
  zip: string;
  phone?: string;
}

export interface BillingAddress extends ShippingAddress {}

export interface LineItem {
  id: string;
  variant_id: string;
  product_id: string;
  title: string;
  variant_title?: string;
  quantity: number;
  price: number;
  sku?: string;
  vendor?: string;
  properties?: { [key: string]: any };
}
