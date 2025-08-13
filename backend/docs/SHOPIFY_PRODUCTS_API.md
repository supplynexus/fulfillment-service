# Shopify Products API

基于 Shopify GraphQL Admin API 的产品管理服务。

## 🚀 功能特性

- ✅ **产品列表获取** - 支持分页和过滤
- ✅ **单个产品详情** - 完整的产品信息
- ✅ **产品搜索** - 基于关键词搜索
- ✅ **按类型过滤** - 按产品类型筛选
- ✅ **按供应商过滤** - 按供应商筛选
- ✅ **按标签过滤** - 按产品标签筛选
- ✅ **按状态过滤** - 按产品状态筛选
- ✅ **连接测试** - API 连接验证

## 📋 API 端点

### 1. 获取产品列表

```http
GET /api/v1/shopify/products?tenant_id=1&limit=10&after=cursor
```

**参数:**
- `tenant_id` (必需): 租户 ID
- `limit` (可选): 返回数量，默认 10，最大 50
- `after` (可选): 分页游标

**响应示例:**
```json
{
  "success": true,
  "data": {
    "products": {
      "nodes": [
        {
          "id": "gid://shopify/Product/123456789",
          "title": "Sample Product",
          "handle": "sample-product",
          "description": "Product description",
          "productType": "Clothing",
          "vendor": "Sample Vendor",
          "status": "ACTIVE",
          "priceRangeV2": {
            "minVariantPrice": {
              "amount": "29.99",
              "currencyCode": "USD"
            },
            "maxVariantPrice": {
              "amount": "29.99",
              "currencyCode": "USD"
            }
          },
          "variants": {
            "nodes": [
              {
                "id": "gid://shopify/ProductVariant/987654321",
                "title": "Default Title",
                "sku": "SAMPLE-001",
                "price": "29.99"
              }
            ]
          }
        }
      ],
      "pageInfo": {
        "hasNextPage": true,
        "hasPreviousPage": false,
        "startCursor": "cursor1",
        "endCursor": "cursor2"
      }
    }
  },
  "message": "Products retrieved successfully"
}
```

### 2. 获取单个产品

```http
GET /api/v1/shopify/products/{product_id}?tenant_id=1
```

**参数:**
- `product_id` (路径): Shopify 产品 ID
- `tenant_id` (必需): 租户 ID

### 3. 搜索产品

```http
GET /api/v1/shopify/products/search?tenant_id=1&q=search_term&limit=10
```

**参数:**
- `tenant_id` (必需): 租户 ID
- `q` (必需): 搜索关键词
- `limit` (可选): 返回数量，默认 10

### 4. 按产品类型过滤

```http
GET /api/v1/shopify/products/type/{product_type}?tenant_id=1&limit=10
```

**参数:**
- `product_type` (路径): 产品类型
- `tenant_id` (必需): 租户 ID
- `limit` (可选): 返回数量

### 5. 按供应商过滤

```http
GET /api/v1/shopify/products/vendor/{vendor}?tenant_id=1&limit=10
```

**参数:**
- `vendor` (路径): 供应商名称
- `tenant_id` (必需): 租户 ID
- `limit` (可选): 返回数量

### 6. 按标签过滤

```http
GET /api/v1/shopify/products/tag/{tag}?tenant_id=1&limit=10
```

**参数:**
- `tag` (路径): 产品标签
- `tenant_id` (必需): 租户 ID
- `limit` (可选): 返回数量

### 7. 按状态过滤

```http
GET /api/v1/shopify/products/status/{status}?tenant_id=1&limit=10
```

**参数:**
- `status` (路径): 产品状态 (ACTIVE, DRAFT, ARCHIVED)
- `tenant_id` (必需): 租户 ID
- `limit` (可选): 返回数量

### 8. 测试连接

```http
GET /api/v1/shopify/products/test-connection?tenant_id=1
```

**参数:**
- `tenant_id` (必需): 租户 ID

## 🔧 认证

所有端点都需要时间戳签名认证：

```bash
# 生成签名
curl -X POST http://localhost:8000/api/v1/auth/generate-signature \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "private_key": "your_private_key",
    "timestamp": 1234567890,
    "nonce": "unique_nonce"
  }'

# 使用签名调用 API
curl -X GET "http://localhost:8000/api/v1/shopify/products?tenant_id=1" \
  -H "X-Tenant-ID: 1" \
  -H "X-Timestamp: 1234567890" \
  -H "X-Nonce: unique_nonce" \
  -H "X-Signature: generated_signature"
```

## 📊 数据字段

### 产品字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | Shopify 产品 ID |
| `title` | String | 产品标题 |
| `handle` | String | 产品 URL 句柄 |
| `description` | String | 产品描述 |
| `descriptionHtml` | String | HTML 格式描述 |
| `productType` | String | 产品类型 |
| `vendor` | String | 供应商 |
| `tags` | Array | 产品标签 |
| `status` | String | 产品状态 |
| `createdAt` | DateTime | 创建时间 |
| `updatedAt` | DateTime | 更新时间 |
| `publishedAt` | DateTime | 发布时间 |
| `totalInventory` | Int | 总库存 |
| `tracksInventory` | Boolean | 是否跟踪库存 |
| `priceRangeV2` | Object | 价格范围 |

### 变体字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 变体 ID |
| `title` | String | 变体标题 |
| `sku` | String | SKU |
| `barcode` | String | 条形码 |
| `price` | String | 价格 |
| `compareAtPrice` | String | 比较价格 |
| `inventoryQuantity` | Int | 库存数量 |
| `selectedOptions` | Array | 选中的选项 |

### 媒体字段

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | String | 媒体 ID |
| `alt` | String | 替代文本 |
| `mediaContentType` | String | 媒体类型 |
| `image.url` | String | 图片 URL |
| `image.width` | Int | 图片宽度 |
| `image.height` | Int | 图片高度 |

## 🧪 测试

运行测试脚本：

```bash
cd backend
python test_shopify_products.py
```

## 📝 使用示例

### Python 示例

```python
import httpx
import asyncio

async def get_products():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/shopify/products",
            params={"tenant_id": 1, "limit": 5},
            headers={
                "X-Tenant-ID": "1",
                "X-Timestamp": "1234567890",
                "X-Nonce": "unique_nonce",
                "X-Signature": "generated_signature"
            }
        )
        return response.json()

# 运行
result = asyncio.run(get_products())
print(result)
```

### cURL 示例

```bash
# 获取产品列表
curl -X GET "http://localhost:8000/api/v1/shopify/products?tenant_id=1&limit=5" \
  -H "X-Tenant-ID: 1" \
  -H "X-Timestamp: 1234567890" \
  -H "X-Nonce: unique_nonce" \
  -H "X-Signature: generated_signature"

# 搜索产品
curl -X GET "http://localhost:8000/api/v1/shopify/products/search?tenant_id=1&q=shirt" \
  -H "X-Tenant-ID: 1" \
  -H "X-Timestamp: 1234567890" \
  -H "X-Nonce: unique_nonce" \
  -H "X-Signature: generated_signature"

# 按状态过滤
curl -X GET "http://localhost:8000/api/v1/shopify/products/status/ACTIVE?tenant_id=1" \
  -H "X-Tenant-ID: 1" \
  -H "X-Timestamp: 1234567890" \
  -H "X-Nonce: unique_nonce" \
  -H "X-Signature: generated_signature"
```

## 🔗 相关文档

- [Shopify GraphQL Admin API](https://shopify.dev/docs/api/admin-graphql)
- [Products Query](https://shopify.dev/docs/api/admin-graphql/unstable/queries/products)
- [Product Object](https://shopify.dev/docs/api/admin-graphql/unstable/objects/Product)
