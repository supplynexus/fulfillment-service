# Shopify 测试订单创建总结

## 已完成的工作

### 1. 成功创建的测试订单

我们成功创建了 3 个测试订单，用于测试 fulfillment service：

#### 订单 #1001 (基础测试订单)
- **订单 ID**: 5787619917924
- **订单号**: #1001
- **状态**: pending
- **履约状态**: unfulfilled
- **总金额**: ¥79.97 CNY
- **商品**: 
  - 测试产品 - T恤 x2 (¥29.99)
  - 测试产品 - 帽子 x1 (¥19.99)
- **备注**: 这是一个测试订单，用于测试 fulfillment service
- **链接**: https://x0ri77-4v.myshopify.com/admin/orders/5787619917924

#### 订单 #1002 (多商品测试订单)
- **订单 ID**: 5787620900964
- **订单号**: #1002
- **状态**: pending
- **履约状态**: unfulfilled
- **总金额**: ¥127.94 CNY
- **商品**:
  - 测试产品 - T恤 x2 (¥29.99)
  - 测试产品 - 帽子 x1 (¥19.99)
  - 测试产品 - 手机壳 x3 (¥15.99)
- **备注**: 多商品测试订单
- **链接**: https://x0ri77-4v.myshopify.com/admin/orders/5787620900964

#### 订单 #1003 (已支付测试订单)
- **订单 ID**: 5787620966500
- **订单号**: #1003
- **状态**: paid
- **履约状态**: unfulfilled
- **总金额**: ¥99.99 CNY
- **商品**:
  - 测试产品 - 高级T恤 x1 (¥99.99)
- **备注**: 已支付测试订单
- **链接**: https://x0ri77-4v.myshopify.com/admin/orders/5787620966500

### 2. 创建的脚本工具

#### 主要脚本文件
1. **`create_shopify_test_order.py`** - 简单的订单创建脚本
2. **`shopify_order_manager.py`** - 完整的订单管理工具
3. **`quick_create_order.sh`** - 快速创建订单的 shell 脚本

#### 功能特性
- ✅ 支持从数据库获取 access token
- ✅ 支持使用提供的 token
- ✅ 多种订单模板 (basic, multi_items, paid)
- ✅ 订单列表查看功能
- ✅ 详细的错误处理和日志
- ✅ 命令行参数支持

### 3. 使用的技术栈

#### Shopify API
- **API 版本**: 2025-07
- **端点**: `/admin/api/2025-07/orders.json`
- **认证方式**: X-Shopify-Access-Token
- **数据格式**: JSON

#### 项目集成
- **数据库**: PostgreSQL (支持从 external_systems 表获取 token)
- **加密**: 使用项目现有的加密/解密功能
- **异步**: 使用 aiohttp 进行异步 HTTP 请求
- **配置**: 集成项目的配置系统

## 使用方法

### 快速创建订单
```bash
# 在 backend 目录下运行
./scripts/quick_create_order.sh
```

### 命令行工具
```bash
# 创建基础测试订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template basic

# 创建多商品测试订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template multi_items

# 创建已支付测试订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action create --template paid

# 列出订单
PYTHONPATH=. python scripts/shopify_order_manager.py --action list --limit 5
```

### 从数据库获取 token
```bash
PYTHONPATH=. python scripts/shopify_order_manager.py --use-db
```

## 配置信息

### 商店信息
- **商店名称**: x0ri77-4v
- **Access Token**: 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
- **API 基础 URL**: https://x0ri77-4v.myshopify.com/admin/api/2025-07

### 订单模板
1. **basic**: 基础测试订单，包含 1 个商品
2. **multi_items**: 多商品测试订单，包含 3 个不同商品
3. **paid**: 已支付测试订单，状态为 paid

## 测试场景覆盖

### 订单状态测试
- ✅ pending 状态订单
- ✅ paid 状态订单

### 商品数量测试
- ✅ 单商品订单
- ✅ 多商品订单
- ✅ 不同数量组合

### 客户信息测试
- ✅ 中文姓名
- ✅ 中国地址
- ✅ 国际格式电话号码

### 订单属性测试
- ✅ 订单备注
- ✅ 订单标签
- ✅ 货币设置 (CNY)

## 下一步计划

### 1. 集成到 fulfillment service
- 将创建的测试订单同步到本地数据库
- 测试订单处理流程
- 验证 webhook 处理

### 2. 扩展测试场景
- 添加更多订单状态 (cancelled, refunded)
- 测试不同地区的订单
- 测试复杂的商品变体

### 3. 自动化测试
- 创建自动化测试脚本
- 集成到 CI/CD 流程
- 定期清理测试订单

## 注意事项

1. **电话号码格式**: 必须使用国际格式 (+86 138 0013 8000)
2. **Python 路径**: 运行脚本时需要设置 `PYTHONPATH=.`
3. **虚拟环境**: 确保在正确的虚拟环境中运行
4. **API 权限**: access token 需要具有创建订单的权限
5. **网络连接**: 确保能够访问 Shopify API

## 相关文档

- [Shopify Admin API 文档](https://shopify.dev/docs/api/admin-graphql/latest/queries/order)
- [使用说明文档](README_SHOPIFY_ORDERS.md)
- [项目架构文档](../docs/ARCHITECTURE.md)
