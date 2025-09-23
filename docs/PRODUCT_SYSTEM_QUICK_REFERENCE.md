# 核心商品系统快速参考

## 表结构概览

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `products` | 商品主表 | id, tenant_id, title, handle, status |
| `product_dimensions` | 商品维度表 | dimension_name, dimension_type, options |
| `product_variants` | 商品变体表 | sku, attributes, price, inventory_quantity |
| `variant_attributes` | 变体属性表 | variant_id, dimension_id, value |
| `external_products` | 外部商品表 | external_product_id, external_data, sync_status |
| `product_mappings` | 商品映射表 | core_product_id, external_product_id, sync_direction |

## Shopify商品转换示例

### 输入数据
```json
{
  "id": "gid://shopify/Product/8040175042660",
  "title": "Unisex Oversized Boxy Tee",
  "handle": "unisex-oversized-boxy-tee",
  "variant": {
    "id": "gid://shopify/ProductVariant/45663476547684",
    "title": "Black / S",
    "price": "41.17",
    "inventory_quantity": 0
  }
}
```

### 转换结果

#### 1. 核心商品 (products)
```sql
INSERT INTO products (tenant_id, title, handle, product_type, status) 
VALUES (1, 'Unisex Oversized Boxy Tee', 'unisex-oversized-boxy-tee', 'Apparel', 'active');
```

#### 2. 商品维度 (product_dimensions)
```sql
-- 颜色维度
INSERT INTO product_dimensions (tenant_id, product_id, dimension_name, dimension_type, options) 
VALUES (1, 1, 'color', 'select', '["Black", "White", "Red", "Blue", "Green"]');

-- 尺寸维度  
INSERT INTO product_dimensions (tenant_id, product_id, dimension_name, dimension_type, options) 
VALUES (1, 1, 'size', 'select', '["XS", "S", "M", "L", "XL", "XXL"]');
```

#### 3. 商品变体 (product_variants)
```sql
INSERT INTO product_variants (tenant_id, product_id, sku, attributes, price, inventory_quantity) 
VALUES (1, 1, 'SHOPIFY-8040175042660-45663476547684', '{"color": "Black", "size": "S"}', 41.17, 0);
```

#### 4. 变体属性 (variant_attributes)
```sql
-- 颜色属性
INSERT INTO variant_attributes (tenant_id, variant_id, dimension_id, value) 
VALUES (1, 1, 1, 'Black');

-- 尺寸属性
INSERT INTO variant_attributes (tenant_id, variant_id, dimension_id, value) 
VALUES (1, 1, 2, 'S');
```

#### 5. 外部商品 (external_products)
```sql
INSERT INTO external_products (tenant_id, external_system_id, external_product_id, title, external_data) 
VALUES (1, 1, 'gid://shopify/Product/8040175042660', 'Unisex Oversized Boxy Tee', '{"id": "gid://shopify/Product/8040175042660", ...}');
```

#### 6. 商品映射 (product_mappings)
```sql
INSERT INTO product_mappings (tenant_id, core_product_id, external_system_id, external_product_id, mapping_type) 
VALUES (1, 1, 1, 'gid://shopify/Product/8040175042660', 'sync');
```

## 常用查询

### 查询商品及其变体
```sql
SELECT p.title, v.sku, v.attributes, v.price 
FROM products p 
JOIN product_variants v ON p.id = v.product_id 
WHERE p.tenant_id = 1;
```

### 查询特定属性的变体
```sql
SELECT v.* FROM product_variants v 
WHERE v.attributes->>'color' = 'Black' 
AND v.attributes->>'size' = 'S';
```

### 查询外部商品映射
```sql
SELECT p.title, pm.external_product_id, ep.sync_status 
FROM products p 
JOIN product_mappings pm ON p.id = pm.core_product_id 
JOIN external_products ep ON pm.external_product_id = ep.external_product_id 
WHERE p.tenant_id = 1;
```

## 系统特点

- ✅ **多租户隔离**: 所有表都有 `tenant_id`
- ✅ **灵活维度**: 支持任意商品属性
- ✅ **混合存储**: JSON + 关系表
- ✅ **外部集成**: 支持多种外部系统
- ✅ **双向同步**: 核心系统与外部系统数据同步
- ✅ **商品组合**: 支持复合商品
- ✅ **标签系统**: 灵活的商品分类
- ✅ **条码管理**: 支持多种条码类型
