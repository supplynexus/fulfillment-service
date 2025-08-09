export interface DashboardStats {
  total_orders: number;
  pending_orders: number;
  processing_orders: number;
  fulfilled_orders: number;
  failed_orders: number;
  total_customers: number;
  active_customers: number;
  total_revenue: number;
  monthly_revenue: number;
  weekly_revenue: number;
  daily_revenue: number;
  fulfillment_rate: number;
  avg_processing_time: number;
}

export interface MetricData {
  date: string;
  orders: number;
  revenue: number;
  fulfillment_rate: number;
}

export interface RevenueMetrics {
  daily: MetricData[];
  weekly: MetricData[];
  monthly: MetricData[];
}

export interface OrderMetrics {
  by_status: { [key: string]: number };
  by_customer: { customer_name: string; order_count: number }[];
  processing_times: number[];
}
