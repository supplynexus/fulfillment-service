# 核心商品系统架构文档

## 概述

本文档详细说明了 SupplyNexus 核心商品系统的架构设计，包括表结构、数据关系、业务逻辑和实际应用案例。该系统支持灵活的商品维度管理、变体控制、多条码系统、标签分类、商品组合和外部系统映射。

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        核心商品系统架构                            │
├─────────────────────────────────────────────────────────────────┤
│  Product (商品主表)                                               │
│  ├── ProductDimension (商品维度表)                               │
│  │   └── VariantAttribute (变体属性表)                          │
│  ├── ProductVariant (商品变体表)                                │
│  │   ├── VariantBarcode (变体条码表)                            │
│  │   └── BarcodeType (条码类型表)                               │
│  ├── ProductTag (商品标签关联表)                                │
│  │   └── Tag (标签表)                                           │
│  ├── ProductCombination (商品组合表)                            │
│  │   └── ProductCombinationItem (商品组合项表)                  │
│  ├── ProductMapping (商品映射表)                                │
│  └── ExternalProduct (外部商品表)                               │
└─────────────────────────────────────────────────────────────────┘
```

## 核心表结构详解

### 1. Product (商品主表)

**用途**: 存储商品的基本信息，作为整个商品系统的根节点。

**关键字段**:
- `id`: 主键
- `tenant_id`: 租户ID（多租户隔离）
- `title`: 商品标题
- `handle`: URL句柄
- `product_type`: 商品类型
- `vendor`: 供应商/品牌
- `status`: 商品状态（draft/active/inactive/archived）
- `images`: 商品图片（JSON）
- `seo`: SEO信息（JSON）

**实际案例**:
```json
{
  "id": 1,
  "tenant_id": 1,
  "title": "Unisex Oversized Boxy Tee",
  "handle": "unisex-oversized-boxy-tee",
  "product_type": "Apparel",
  "vendor": "Unknown",
  "status": "active",
  "images": [{"url": "https://cdn.shopify.com/...", "alt_text": ""}],
  "seo": {"currency": "USD"}
}
```

### 2. ProductDimension (商品维度表)

**用途**: 定义商品的可变维度，如颜色、尺寸、材质等。

**关键字段**:
- `dimension_name`: 维度名称（如：color, size, material）
- `dimension_type`: 维度类型（select/text/number/boolean）
- `options`: 选项列表（用于select类型）
- `is_required`: 是否必填
- `display_order`: 显示顺序

**实际案例**:
```json
// 颜色维度
{
  "id": 1,
  "product_id": 1,
  "dimension_name": "color",
  "dimension_type": "select",
  "display_name": "颜色",
  "options": ["Black", "White", "Red", "Blue", "Green"],
  "is_required": true,
  "display_order": 1
}

// 尺寸维度
{
  "id": 2,
  "product_id": 1,
  "dimension_name": "size",
  "dimension_type": "select",
  "display_name": "尺寸",
  "options": ["XS", "S", "M", "L", "XL", "XXL"],
  "is_required": true,
  "display_order": 2
}
```

### 3. ProductVariant (商品变体表)

**用途**: 存储具体的商品变体（SKU级别），每个变体代表一个具体的商品规格。

**关键字段**:
- `sku`: 商品SKU
- `barcode`: 主要条码
- `attributes`: 变体属性（JSON存储，用于快速查询）
- `price`: 价格
- `inventory_quantity`: 库存数量
- `image_url`: 变体图片

**实际案例**:
```json
{
  "id": 1,
  "product_id": 1,
  "sku": "SHOPIFY-8040175042660-45663476547684",
  "barcode": null,
  "attributes": {"color": "Black", "size": "S"},
  "price": 41.17,
  "inventory_quantity": 0,
  "image_url": "https://cdn.shopify.com/..."
}
```

### 4. VariantAttribute (变体属性表)

**用途**: 存储变体的具体属性值，支持复杂的属性查询和过滤。

**关键字段**:
- `variant_id`: 变体ID
- `dimension_id`: 维度ID
- `value`: 属性值
- `display_value`: 显示值

**实际案例**:
```json
// 颜色属性
{
  "id": 1,
  "variant_id": 1,
  "dimension_id": 1,
  "value": "Black",
  "display_value": "Black"
}

// 尺寸属性
{
  "id": 2,
  "variant_id": 1,
  "dimension_id": 2,
  "value": "S",
  "display_value": "S"
}
```

### 5. ExternalProduct (外部商品表)

**用途**: 存储外部系统（如Shopify、Printify）的商品数据，保持原始格式。

**关键字段**:
- `external_system_id`: 外部系统ID
- `external_product_id`: 外部系统商品ID
- `external_variant_id`: 外部系统变体ID
- `external_data`: 外部系统原始数据（JSON）
- `sync_status`: 同步状态

**实际案例**:
```json
{
  "id": 1,
  "external_system_id": 1,
  "external_product_id": "gid://shopify/Product/8040175042660",
  "external_variant_id": "gid://shopify/ProductVariant/45663476547684",
  "title": "Unisex Oversized Boxy Tee",
  "external_data": {
    "id": "gid://shopify/Product/8040175042660",
    "title": "Unisex Oversized Boxy Tee",
    "handle": "unisex-oversized-boxy-tee",
    "status": "ACTIVE",
    "price": "41.17",
    "currency": "USD",
    "variant": {
      "id": "gid://shopify/ProductVariant/45663476547684",
      "title": "Black / S",
      "price": "41.17",
      "inventory_quantity": 0
    }
  },
  "sync_status": "synced"
}
```

### 6. ProductMapping (商品映射表)

**用途**: 建立核心商品与外部系统商品的映射关系，支持双向同步。

**关键字段**:
- `core_product_id`: 核心商品ID
- `core_variant_id`: 核心变体ID
- `external_system_id`: 外部系统ID
- `external_product_id`: 外部商品ID
- `mapping_type`: 映射类型（sync/manual/auto）
- `sync_direction`: 同步方向（to_external/from_external/bidirectional）

**实际案例**:
```json
{
  "id": 1,
  "core_product_id": 1,
  "core_variant_id": 1,
  "external_system_id": 1,
  "external_product_id": "gid://shopify/Product/8040175042660",
  "external_variant_id": "gid://shopify/ProductVariant/45663476547684",
  "mapping_type": "sync",
  "sync_direction": "bidirectional",
  "sync_status": "synced"
}
```

## 业务逻辑说明

### 1. 商品创建流程

```
1. 创建核心商品 (Product)
   ↓
2. 定义商品维度 (ProductDimension)
   ↓
3. 创建商品变体 (ProductVariant)
   ↓
4. 设置变体属性 (VariantAttribute)
   ↓
5. 存储外部商品数据 (ExternalProduct)
   ↓
6. 建立映射关系 (ProductMapping)
```

### 2. 数据查询策略

#### 快速查询（使用JSON字段）
```sql
-- 查询所有黑色S码的变体
SELECT * FROM product_variants 
WHERE attributes->>'color' = 'Black' 
AND attributes->>'size' = 'S';
```

#### 精确查询（使用关系表）
```sql
-- 查询特定维度的变体
SELECT v.* FROM product_variants v
JOIN variant_attributes va ON v.id = va.variant_id
JOIN product_dimensions pd ON va.dimension_id = pd.id
WHERE pd.dimension_name = 'color' 
AND va.value = 'Black';
```

### 3. 多租户隔离

所有表都包含 `tenant_id` 字段，确保数据隔离：

```sql
-- 查询租户1的所有商品
SELECT * FROM products WHERE tenant_id = 1;

-- 查询租户1的特定变体
SELECT * FROM product_variants WHERE tenant_id = 1;
```

## 实际应用案例：Shopify商品转换

### 输入数据（Shopify商品）
```json
{
  "id": "gid://shopify/Product/8040175042660",
  "title": "Unisex Oversized Boxy Tee",
  "handle": "unisex-oversized-boxy-tee",
  "status": "ACTIVE",
  "price": "41.17",
  "currency": "USD",
  "variant": {
    "id": "gid://shopify/ProductVariant/45663476547684",
    "title": "Black / S",
    "price": "41.17",
    "inventory_quantity": 0
  }
}
```

### 转换后的核心系统数据

#### 1. 核心商品记录
```sql
INSERT INTO products (
  tenant_id, title, handle, product_type, vendor, status, 
  is_active, is_available, images, seo
) VALUES (
  1, 'Unisex Oversized Boxy Tee', 'unisex-oversized-boxy-tee', 
  'Apparel', 'Unknown', 'active', true, true,
  '[{"url": "https://cdn.shopify.com/..."}]',
  '{"currency": "USD"}'
);
```

#### 2. 商品维度定义
```sql
-- 颜色维度
INSERT INTO product_dimensions (
  tenant_id, product_id, dimension_name, dimension_type, 
  display_name, options, is_required, display_order
) VALUES (
  1, 1, 'color', 'select', '颜色', 
  '["Black", "White", "Red", "Blue", "Green"]', 
  true, 1
);

-- 尺寸维度
INSERT INTO product_dimensions (
  tenant_id, product_id, dimension_name, dimension_type, 
  display_name, options, is_required, display_order
) VALUES (
  1, 1, 'size', 'select', '尺寸', 
  '["XS", "S", "M", "L", "XL", "XXL"]', 
  true, 2
);
```

#### 3. 商品变体记录
```sql
INSERT INTO product_variants (
  tenant_id, product_id, sku, attributes, price, 
  inventory_quantity, is_active, is_available
) VALUES (
  1, 1, 'SHOPIFY-8040175042660-45663476547684',
  '{"color": "Black", "size": "S"}', 41.17, 0, true, true
);
```

#### 4. 变体属性记录
```sql
-- 颜色属性
INSERT INTO variant_attributes (
  tenant_id, variant_id, dimension_id, value, display_value
) VALUES (1, 1, 1, 'Black', 'Black');

-- 尺寸属性
INSERT INTO variant_attributes (
  tenant_id, variant_id, dimension_id, value, display_value
) VALUES (1, 1, 2, 'S', 'S');
```

#### 5. 外部商品记录
```sql
INSERT INTO external_products (
  tenant_id, external_system_id, external_product_id, 
  external_variant_id, title, external_data, sync_status
) VALUES (
  1, 1, 'gid://shopify/Product/8040175042660',
  'gid://shopify/ProductVariant/45663476547684',
  'Unisex Oversized Boxy Tee',
  '{"id": "gid://shopify/Product/8040175042660", ...}',
  'synced'
);
```

#### 6. 映射关系记录
```sql
INSERT INTO product_mappings (
  tenant_id, core_product_id, core_variant_id, 
  external_system_id, external_product_id, external_variant_id,
  mapping_type, sync_direction, sync_status
) VALUES (
  1, 1, 1, 1, 
  'gid://shopify/Product/8040175042660',
  'gid://shopify/ProductVariant/45663476547684',
  'sync', 'bidirectional', 'synced'
);
```

## 系统优势

### 1. 灵活性
- **可变维度**: 支持任意维度的商品属性
- **动态扩展**: 新增维度无需修改表结构
- **混合存储**: JSON + 关系表，兼顾性能和查询能力

### 2. 可扩展性
- **多租户隔离**: 完整的租户数据隔离
- **外部系统集成**: 支持多种外部平台
- **双向同步**: 核心系统与外部系统数据同步

### 3. 性能优化
- **索引策略**: 针对查询场景优化的索引
- **JSON查询**: 支持快速的属性查询
- **关系查询**: 支持复杂的关联查询

### 4. 业务完整性
- **商品组合**: 支持复合商品（BOM）
- **标签系统**: 灵活的商品分类和检索
- **条码管理**: 支持多种条码类型
- **映射关系**: 完整的内外部商品关联

## 使用建议

### 1. 数据建模
- 根据业务需求定义合适的商品维度
- 合理使用JSON字段和关系表
- 建立适当的索引策略

### 2. 查询优化
- 简单查询使用JSON字段
- 复杂查询使用关系表
- 考虑查询频率和性能要求

### 3. 数据同步
- 建立清晰的同步策略
- 处理同步冲突和错误
- 监控同步状态和性能

### 4. 扩展开发
- 新增维度时考虑向后兼容
- 保持数据一致性
- 测试各种边界情况

## 总结

新的核心商品系统架构提供了强大而灵活的商品管理能力，支持复杂的业务需求，同时保持了良好的性能和可扩展性。通过合理的表结构设计和业务逻辑，系统能够处理各种商品管理场景，为业务发展提供坚实的技术基础。
