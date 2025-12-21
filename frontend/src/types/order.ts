export interface Order {
  id?: number; // 保留原始ID（可选）
  id_hashid: string; // 添加hashid字段
  order_number: string; // 添加订单编号字段
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
  carrier?: string;
  fulfillment_status?: string;
   address_validation_status?:
    | 'not_checked'
    | 'valid'
    | 'invalid'
    | 'suspicious'
    | 'failed';
  address_validation_reason_code?: string;
  address_validation_message?: string;
  address_last_validated_at?: string;
  order_date: string;
  processed_at?: string;
  fulfilled_at?: string;
  created_at: string;
  updated_at?: string;
  customer_id?: number;
  scm_orders_count?: number; // 关联的 SCM 订单数量
  raw_data?: {
    fulfillments?: any[];
    tracking_number?: string;
    tracking_url?: string;
    carrier?: string;
    [key: string]: any;
  };
  external_data?: {
    fulfillments?: any[];
    tracking_number?: string;
    tracking_url?: string;
    carrier?: string;
    [key: string]: any;
  };
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
  variant_id?: string;
  product_id?: string;
  title: string;
  variant_title?: string;
  quantity: number;
  price: number;
  cost?: number;
  sku?: string;
  vendor?: string;
  properties?: { [key: string]: any };
  // 核心系统ID
  core_product_id?: string;
  core_variant_id?: string;
  // 外部系统ID
  external_product_id?: string;
  external_variant_id?: string;
  // 其他字段
  fulfillment_status?: string;
  item_metadata?: { [key: string]: any };
}
