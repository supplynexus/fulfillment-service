# Shopify 订单管理脚本使用说明

## 概述

这个脚本提供了创建和管理 Shopify 测试订单的功能，支持从数据库获取 access token 或使用提供的 token。

## 脚本文件

- `create_shopify_test_order.py` - 简单的订单创建脚本
- `shopify_order_manager.py` - 完整的订单管理工具

## 使用方法

### 1. 简单订单创建

```bash
# 使用默认 token 创建基础测试订单
PYTHONPATH=. python scripts/create_shopify_test_order.py
```

### 2. 完整订单管理工具

#### 创建订单

```bash
# 创建基础测试订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template basic

# 创建多商品测试订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template multi_items

# 创建已支付测试订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template paid
```

#### 列出订单

```bash
# 列出最近 10 个订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action list

# 列出最近 5 个订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action list --limit 5
```

#### 使用自定义参数

```bash
# 使用自定义商店名称
PYTHONPATH=. python scripts/shopify_order_manager.py --shop your-shop-name

# 使用自定义 access token
PYTHONPATH=. python scripts/shopify_order_manager.py --token your-access-token

# 从数据库获取 access token
PYTHONPATH=. python scripts/shopify_order_manager.py --use-db
```

## 订单模板类型

### 1. basic - 基础测试订单
- 1 个商品：测试产品 - T恤 (2件)
- 状态：pending
- 履约状态：unfulfilled
- 总金额：¥59.98

### 2. multi_items - 多商品测试订单
- 3 个商品：
  - 测试产品 - T恤 (2件)
  - 测试产品 - 帽子 (1件)
  - 测试产品 - 手机壳 (3件)
- 状态：pending
- 履约状态：unfulfilled
- 总金额：¥127.94

### 3. paid - 已支付测试订单
- 1 个商品：测试产品 - 高级T恤 (1件)
- 状态：paid
- 履约状态：unfulfilled
- 总金额：¥99.99

## 配置说明

### 默认配置
- 商店名称：x0ri77-4v
- Access Token：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

### 数据库配置
脚本支持从数据库获取 Shopify access token，需要：
1. 在 `external_systems` 表中配置 Shopify 类型的外部系统
2. 在 `credentials` 字段中存储加密的 access_token
3. 使用 `--use-db` 参数强制从数据库获取

## 输出示例

### 创建订单成功
```
🚀 Shopify 订单管理工具
🔑 使用默认 access token: shpat_4bdbb12d6e43a4...
📦 创建 multi_items 类型的测试订单...
🌐 发送请求到: https://x0ri77-4v.myshopify.com/admin/api/2025-07/orders.json
📡 响应状态: 201
✅ 订单创建成功!

📋 订单详情:
  订单 ID: 5787620900964
  订单号: #1002
  邮箱: test@example.com
  状态: pending
  履约状态: None
  总金额: 127.94 CNY
  创建时间: 2025-08-13T22:13:33-04:00

📦 商品列表:
  - 测试产品 - T恤 x2 (¥29.99)
  - 测试产品 - 帽子 x1 (¥19.99)
  - 测试产品 - 手机壳 x3 (¥15.99)

✅ 测试订单创建完成!
🔗 订单链接: https://x0ri77-4v.myshopify.com/admin/orders/5787620900964
```

### 列出订单
```
🚀 Shopify 订单管理工具
🔑 使用默认 access token: shpat_4bdbb12d6e43a4...
📋 获取最近 5 个订单...

📋 找到 3 个订单:
  - #1003 (ID: 5787620966500) - paid - ¥99.99
    邮箱: test@example.com | 创建时间: 2025-08-13T22:13:38-04:00
    备注: 已支付测试订单

  - #1002 (ID: 5787620900964) - pending - ¥127.94
    邮箱: test@example.com | 创建时间: 2025-08-13T22:13:33-04:00
    备注: 多商品测试订单

  - #1001 (ID: 5787619917924) - pending - ¥79.97
    邮箱: test@example.com | 创建时间: 2025-08-13T22:12:12-04:00
    备注: 这是一个测试订单，用于测试 fulfillment service
```

## 注意事项

1. **Python 路径**：运行脚本时需要设置 `PYTHONPATH=.` 以正确导入应用模块
2. **虚拟环境**：确保在正确的虚拟环境中运行脚本
3. **权限**：确保 access token 具有创建订单的权限
4. **网络**：确保能够访问 Shopify API
5. **电话号码格式**：使用国际格式，如 `+86 138 0013 8000`

## 错误处理

### 常见错误
- `422` 错误：通常是由于数据格式问题（如电话号码格式）
- `401` 错误：access token 无效或过期
- `403` 错误：权限不足

### 调试
- 脚本会显示详细的请求和响应信息
- 使用 `--help` 查看所有可用选项
- 检查网络连接和 API 权限

## 扩展

### 添加新的订单模板
在 `get_test_order_templates()` 函数中添加新的模板：

```python
"new_template": {
    "order": {
        "email": "test@example.com",
        "financial_status": "pending",
        "fulfillment_status": "unfulfilled",
        "line_items": [
            {
                "title": "新产品",
                "price": "50.00",
                "quantity": 1,
                "sku": "NEW-PRODUCT-001"
            }
        ],
        # ... 其他字段
    }
}
```

### 自定义订单数据
可以修改脚本中的订单数据来满足特定需求，包括：
- 商品信息
- 客户信息
- 地址信息
- 订单备注和标签
