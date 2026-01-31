# 订单自动化功能测试指南

## 🎉 数据清理完成

所有订单数据已成功清理：
- ✅ `orders` 表：0 条记录
- ✅ `scm_orders` 表：0 条记录  
- ✅ `routing_status` 表：0 条记录
- ✅ 自增ID序列已重置

## 🚀 测试步骤

### 步骤1：确认服务状态

```bash
# 检查Docker服务状态
docker-compose ps

# 检查后端服务健康状态
curl http://localhost:8000/health
```

### 步骤2：配置外部系统

确保以下外部系统已正确配置：

#### Shopify系统配置
- 系统类型：`SHOPIFY`
- 必需字段：
  - `access_token`: Shopify访问令牌
  - `store_url`: Shopify商店URL

#### Printify系统配置
- 系统类型：`PRINTIFY`
- 必需字段：
  - `access_token`: Printify访问令牌
  - `shop_id`: Printify商店ID

### 步骤3：同步Shopify订单

```bash
# 手动同步Shopify订单
curl -X POST "http://localhost:8000/api/v1/shopify/sync-orders?tenant_id=1&limit=10"
```

### 步骤4：触发订单自动化流程

#### 方式1：完整自动化流程
```bash
curl -X POST "http://localhost:8000/api/v1/automation/sync-all?tenant_id=1&process_limit=10&sync_limit=20"
```

#### 方式2：分步执行
```bash
# 1. 处理新的Shopify订单
curl -X POST "http://localhost:8000/api/v1/automation/process-shopify-orders?tenant_id=1&limit=10"

# 2. 同步Printify订单状态
curl -X POST "http://localhost:8000/api/v1/automation/sync-printify-status?tenant_id=1&limit=20"

# 3. 同步SCM订单到Shopify履约
curl -X POST "http://localhost:8000/api/v1/automation/sync-shopify-fulfillment?tenant_id=1&limit=20"
```

### 步骤5：监控任务状态

```bash
# 查看任务状态（替换 {task_id} 为实际任务ID）
curl "http://localhost:8000/api/v1/automation/task-status/{task_id}"
```

### 步骤6：验证数据流程

#### 检查订单数据
```sql
-- 在PostgreSQL中执行
docker-compose exec postgres psql -U supplynexus_admin -d supplynexus -c "
SELECT 
    o.id as order_id,
    o.shopify_order_id,
    o.order_number,
    o.status,
    o.fulfillment_status
FROM orders o 
ORDER BY o.created_at DESC 
LIMIT 10;
"
```

#### 检查SCM订单数据
```sql
docker-compose exec postgres psql -U supplynexus_admin -d supplynexus -c "
SELECT 
    s.id as scm_order_id,
    s.scm_order_number,
    s.shopify_order_id,
    s.printify_order_id,
    s.status,
    s.target_system_type
FROM scm_orders s 
ORDER BY s.created_at DESC 
LIMIT 10;
"
```

#### 检查订单追踪链
```sql
docker-compose exec postgres psql -U supplynexus_admin -d supplynexus -c "
SELECT 
    o.id as order_id,
    o.shopify_order_id,
    s.id as scm_order_id,
    s.printify_order_id,
    s.shopify_fulfillment_id
FROM orders o
LEFT JOIN scm_orders s ON o.id = s.source_order_id
ORDER BY o.created_at DESC 
LIMIT 10;
"
```

## 🔍 预期结果

### 正常流程应该看到：

1. **Shopify订单同步**：
   - `orders` 表中有新记录
   - `shopify_order_id` 字段有值

2. **SCM订单创建**：
   - `scm_orders` 表中有新记录
   - `source_order_id` 关联到 `orders.id`
   - `shopify_order_id` 直接引用Shopify订单

3. **Printify订单创建**：
   - `scm_orders.printify_order_id` 有值
   - `target_system_type` 为 "PRINTIFY"

4. **状态同步**：
   - SCM订单状态更新
   - Shopify履约状态更新

## 🐛 故障排除

### 常见问题

1. **没有Shopify订单**：
   - 检查Shopify外部系统配置
   - 确认Shopify商店有订单数据

2. **SCM订单创建失败**：
   - 检查订单路由规则配置
   - 查看后端日志：`docker-compose logs backend`

3. **Printify订单创建失败**：
   - 检查Printify外部系统配置
   - 确认Printify商品ID和变体ID正确

4. **状态同步失败**：
   - 检查外部系统凭据
   - 查看Celery Worker日志：`docker-compose logs celery-worker`

### 查看日志

```bash
# 后端服务日志
docker-compose logs -f backend

# Celery Worker日志
docker-compose logs -f celery-worker

# Celery Beat日志
docker-compose logs -f celery-beat
```

## 📊 监控指标

### 关键指标
- 订单处理成功率
- 各步骤执行时间
- 错误率和重试次数
- 队列长度

### 检查队列状态
```bash
# 访问Flower监控界面
open http://localhost:5555
```

## 🎯 测试场景

### 场景1：正常订单流程
1. 确保有Shopify订单
2. 触发完整自动化流程
3. 验证所有步骤成功执行

### 场景2：错误处理
1. 配置错误的Printify凭据
2. 触发订单处理
3. 验证错误处理和重试机制

### 场景3：批量处理
1. 同步多个Shopify订单
2. 触发批量处理
3. 验证处理性能

## 📝 测试记录

建议记录以下信息：
- 测试时间
- 处理的订单数量
- 各步骤执行时间
- 遇到的错误和解决方案
- 性能指标

---

**注意**：测试过程中如果遇到问题，可以随时重新清理数据并重新开始测试。
