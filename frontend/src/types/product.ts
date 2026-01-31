// ==================== 新的商品系统类型定义 ====================

export interface Product {
  id_hashid: string;
  title: string;
  description?: string;
  handle?: string;
  product_type?: string;
  vendor?: string;
  status: string;
  is_active: boolean;
  is_available: boolean;
  images?: any[];
  seo?: any;
  created_at: string;
  updated_at?: string;

  // 关联数据
  dimensions: ProductDimension[];
  variants: ProductVariant[];
  tags: ProductTag[];
  mappings: ProductMapping[];
}

export interface ProductDimension {
  id_hashid: string;
  dimension_name: string;
  dimension_type: string;
  display_name?: string;
  description?: string;
  options?: string[];
  is_required: boolean;
  display_order: number;
  is_active: boolean;
}

export interface ProductVariant {
  id_hashid: string;
  sku?: string;
  barcode?: string;
  attributes: Record<string, any>;
  price?: number;
  compare_at_price?: number;
  cost_price?: number;
  inventory_quantity: number;
  inventory_policy: string;
  tracks_inventory: boolean;
  is_active: boolean;
  is_available: boolean;
  image_url?: string;
  weight?: number;
  dimensions?: Record<string, any>;
}

export interface ProductTag {
  id_hashid: string;
  name: string;
  display_name?: string;
  color?: string;
  category?: string;
  is_primary: boolean;
  sort_order: number;
}

export interface ProductMapping {
  id_hashid: string;
  external_system_name: string;
  external_product_id: string;
  external_variant_id?: string;
  mapping_type: string;
  sync_direction: string;
  sync_status: string;
  last_synced_at?: string;
}

// ==================== 商品列表响应 ====================

export interface ProductListResponse {
  products: Product[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

// ==================== 创建和更新请求 ====================

export interface ProductCreateRequest {
  title: string;
  description?: string;
  handle?: string;
  product_type?: string;
  vendor?: string;
  status?: string;
  is_active?: boolean;
  is_available?: boolean;
  images?: any[];
  seo?: any;
}

export interface ProductUpdateRequest {
  title?: string;
  description?: string;
  handle?: string;
  product_type?: string;
  vendor?: string;
  status?: string;
  is_active?: boolean;
  is_available?: boolean;
  images?: any[];
  seo?: any;
}

export interface ProductVariantCreateRequest {
  sku?: string;
  barcode?: string;
  attributes?: Record<string, any>;
  price?: number;
  compare_at_price?: number;
  cost_price?: number;
  inventory_quantity?: number;
  inventory_policy?: string;
  tracks_inventory?: boolean;
  is_active?: boolean;
  is_available?: boolean;
  image_url?: string;
  weight?: number;
  dimensions?: Record<string, any>;
}

export interface ProductVariantUpdateRequest {
  sku?: string;
  barcode?: string;
  attributes?: Record<string, any>;
  price?: number;
  compare_at_price?: number;
  cost_price?: number;
  inventory_quantity?: number;
  inventory_policy?: string;
  tracks_inventory?: boolean;
  is_active?: boolean;
  is_available?: boolean;
  image_url?: string;
  weight?: number;
  dimensions?: Record<string, any>;
}

// ==================== 兼容性类型 (保留旧版本) ====================

export interface LegacyProduct {
  id: number;
  printify_product_id: string;
  title: string;
  description?: string;
  tags?: string[];
  images?: string[];
  variants?: LegacyProductVariant[];
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

export interface LegacyProductVariant {
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
