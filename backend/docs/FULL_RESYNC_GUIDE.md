# 数据完全重新同步指南

本文档介绍如何执行Shopify订单和商品的完全重新同步。

## 概述

完全重新同步是指忽略时间过滤条件，从Shopify获取所有可用的订单和商品数据，并同步到本地数据库。这在以下情况下很有用：

- 初始数据导入
- 数据不一致需要重新同步
- 系统升级后需要重新同步
- 手动数据修复

## 智能重试机制

系统内置了智能重试机制来处理Shopify API的速率限制和其他临时错误：

### 重试策略
- **指数退避**：延迟时间按指数增长（2秒 → 4秒 → 8秒 → 16秒 → 32秒）
- **最大延迟**：最多等待60秒
- **随机抖动**：添加±10%的随机延迟，避免多个请求同时重试
- **重试状态码**：429（速率限制）、500、502、503、504

### 重试配置
```python
# 默认重试配置
max_retries = 5          # 最大重试5次
base_delay = 2.0         # 基础延迟2秒
max_delay = 60.0         # 最大延迟60秒
exponential_base = 2.0   # 指数退避基数
jitter = True            # 启用随机抖动
```

### 重试示例
```
尝试 1: 2.0秒延迟
尝试 2: 4.0秒延迟  
尝试 3: 8.0秒延迟
尝试 4: 16.0秒延迟
尝试 5: 32.0秒延迟
尝试 6: 60.0秒延迟（达到最大值）
```

## 同步方式

### 1. API端点方式（推荐）

#### 完全重新同步订单
```bash
# 同步所有订单（不限制数量）
curl -X POST "http://localhost:8000/api/v1/orders/sync/full" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 同步订单（限制数量）
curl -X POST "http://localhost:8000/api/v1/orders/sync" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_recent_only": false,
    "max_orders": 1000
  }'
```

#### 完全重新同步商品
```bash
# 同步所有商品（不限制数量）
curl -X POST "http://localhost:8000/api/v1/products/sync/full" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 同步商品（限制数量）
curl -X POST "http://localhost:8000/api/v1/products/sync" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_recent_only": false,
    "max_products": 500
  }'
```

#### 后台异步同步
```bash
# 后台异步同步订单
curl -X POST "http://localhost:8000/api/v1/orders/sync/background" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_recent_only": false,
    "max_orders": null
  }'

# 后台异步同步商品
curl -X POST "http://localhost:8000/api/v1/products/sync/background" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sync_recent_only": false,
    "max_products": null
  }'
```

### 2. 命令行脚本方式

#### 使用Shell脚本
```bash
# 进入后端目录
cd backend

# 完全重新同步所有数据
./scripts/full_resync.sh

# 只同步订单
./scripts/full_resync.sh --orders-only

# 只同步商品
./scripts/full_resync.sh --products-only

# 限制数量
./scripts/full_resync.sh --max-orders 1000 --max-products 500

# 指定租户
./scripts/full_resync.sh --tenant-id 1

# 查看帮助
./scripts/full_resync.sh --help
```

#### 使用Python脚本
```bash
# 进入后端目录
cd backend

# 完全重新同步所有数据
python3 scripts/full_resync.py

# 只同步订单
python3 scripts/full_resync.py --orders

# 只同步商品
python3 scripts/full_resync.py --products

# 限制数量
python3 scripts/full_resync.py --max-orders 1000 --max-products 500

# 指定租户
python3 scripts/full_resync.py --tenant-id 1

# 查看帮助
python3 scripts/full_resync.py --help
```

### 3. Celery任务方式

#### 直接调用Celery任务
```python
from app.tasks.shopify_tasks import sync_shopify_orders_task, sync_shopify_products_task

# 完全重新同步订单
task = sync_shopify_orders_task.delay(
    tenant_id=1,
    sync_recent_only=False,
    max_orders=None
)

# 完全重新同步商品
task = sync_shopify_products_task.delay(
    tenant_id=1,
    sync_recent_only=False,
    max_products=None
)
```

## 监控同步状态

### 查看任务状态
```bash
# 获取任务状态
curl -X GET "http://localhost:8000/api/v1/sync/tasks/{task_id}" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 查看同步摘要
```bash
# 获取同步摘要
curl -X GET "http://localhost:8000/api/v1/sync/summary" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 查看租户同步状态
```bash
# 获取所有租户的同步状态
curl -X GET "http://localhost:8000/api/v1/sync/status" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 取消正在运行的任务
```bash
# 取消任务
curl -X POST "http://localhost:8000/api/v1/sync/tasks/{task_id}/cancel" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 重置同步时间戳
```bash
# 重置所有租户的同步时间戳
curl -X POST "http://localhost:8000/api/v1/sync/reset-sync-timestamp" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 重置指定租户的同步时间戳
curl -X POST "http://localhost:8000/api/v1/sync/reset-sync-timestamp?tenant_id=1" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 定时任务

系统已经配置了以下定时任务：

### 每小时全量同步
- 订单同步：每小时整点执行
- 商品同步：每小时整点执行
- 限制数量：1000个

### 每日全量同步
- 订单同步：每天凌晨2点执行
- 商品同步：每天凌晨3点执行
- 不限制数量：同步所有数据

## 速率限制处理

### Shopify API限制
- **GraphQL API**：每秒最多2个请求
- **REST API**：每秒最多2个请求
- **Webhook**：每秒最多4个请求

### 系统自动处理
1. **检测429错误**：自动识别速率限制响应
2. **智能等待**：使用指数退避算法等待
3. **幂等性**：确保重试不会产生重复数据
4. **日志记录**：详细记录重试过程

### 重试日志示例
```
2024-01-15 10:30:15 - WARNING - Rate limit hit (429) on attempt 1/6. Retrying in 2.1s.
2024-01-15 10:30:17 - WARNING - Rate limit hit (429) on attempt 2/6. Retrying in 4.3s.
2024-01-15 10:30:22 - INFO - Request successful after 3 attempts
```

## 注意事项

### 性能考虑
1. **数据量**：完全重新同步会获取所有数据，可能耗时较长
2. **API限制**：系统自动处理速率限制，但大量数据仍需要时间
3. **数据库负载**：大量数据写入可能影响数据库性能
4. **内存使用**：处理大量数据时注意内存使用

### 建议
1. **分批处理**：对于大量数据，建议使用`max_orders`和`max_products`参数分批处理
2. **非高峰期**：建议在业务低峰期执行完全重新同步
3. **监控资源**：执行过程中监控系统资源使用情况
4. **备份数据**：执行前建议备份重要数据

### 错误处理
1. **网络错误**：系统自动重试，使用指数退避算法
2. **API错误**：429错误自动处理，其他错误记录在日志中
3. **数据错误**：数据格式错误会被跳过并记录
4. **任务失败**：可以通过API查看任务状态和错误信息

## 故障排除

### 常见问题

1. **同步失败**
   - 检查Shopify API凭据是否正确
   - 检查网络连接
   - 查看日志文件中的重试信息

2. **数据不完整**
   - 检查API速率限制日志
   - 确认Shopify商店中有数据
   - 查看错误日志

3. **任务卡住**
   - 检查Celery工作进程状态
   - 查看Redis连接
   - 重启Celery服务

4. **速率限制频繁**
   - 减少并发请求数量
   - 增加重试间隔时间
   - 检查Shopify API使用情况

### 日志位置
- 应用日志：`logs-dev/` 或 `logs-local/`
- Celery日志：查看Celery工作进程输出
- 数据库日志：查看PostgreSQL日志

### 调试工具
```bash
# 测试重试机制
python3 scripts/test_retry_mechanism.py

# 调试商品同步
python3 debug_product_sync.py

# 调试订单同步
python3 debug_sync_detailed.py

# 测试Shopify API连接
python3 test_shopify_api.py
```

## 最佳实践

1. **定期同步**：使用定时任务保持数据同步
2. **增量同步**：日常使用增量同步，减少资源消耗
3. **监控告警**：设置同步失败告警
4. **数据验证**：定期验证同步数据的完整性
5. **性能优化**：根据数据量调整同步参数
6. **速率限制**：监控API使用情况，避免频繁触发限制
