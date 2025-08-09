export interface Product {
  id: number;
  printify_product_id: string;
  title: string;
  description?: string;
  tags?: string[];
  images?: string[];
  variants?: ProductVariant[];
  price?: number;
  compare_at_price?: number;
  is_active: boolean;
  is_available: boolean;
  print_provider_id?: string;
  print_areas?: any;
  created_at: string;
  updated_at?: string;
  last_synced_at?: string;
}

export interface ProductVariant {
  id: string;
  title: string;
  price: number;
  sku?: string;
  inventory_quantity?: number;
  weight?: number;
  options: VariantOption[];
}

export interface VariantOption {
  name: string;
  value: string;
}

export interface ProductResponse extends Product {}
