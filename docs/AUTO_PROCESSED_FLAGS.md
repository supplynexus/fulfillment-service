# 自动化处理标志说明

## 概述

为了避免自动任务重复处理相同的数据，我们在数据库表中添加了处理标志字段。自动任务只会处理标志为 `FALSE` 的数据，处理成功后会将标志设置为 `TRUE`。

## 标志字段列表

### shopify_orders 表
- `auto_synced_to_core` - 是否已自动同步到核心订单表
- `auto_synced_fulfillment_from_api` - 是否已自动同步发货信息从API
- `auto_synced_fulfillment_to_core` - 是否已自动同步发货信息到核心订单表

### orders 表
- `auto_routed_to_scm` - 是否已自动路由到SCM订单

### scm_orders 表
- `auto_created_printify_order` - 是否已自动创建Printify订单
- `auto_synced_fulfillment_from_printify` - 是否已自动同步发货信息从Printify
- `auto_synced_fulfillment_to_shopify` - 是否已自动同步发货信息到Shopify

### printify_orders 表
- `auto_synced_from_api` - 是否已自动从API同步
- `auto_synced_fulfillment_to_scm` - 是否已自动同步发货信息到SCM订单

## 9个自动化步骤的标志使用

### 1. sync_external_orders (Shopify API → shopify_orders 表)
- **不设置标志** - 此步骤每次都会更新订单数据，不需要标志

### 2. sync_to_core_orders (shopify_orders 表 → orders 表)
- **检查标志**: `shopify_orders.auto_synced_to_core == False`
- **设置标志**: 处理成功后设置 `shopify_orders.auto_synced_to_core = True`

### 3. create_scm_orders (orders 表 → scm_orders 表)
- **检查标志**: `orders.auto_routed_to_scm == False`
- **设置标志**: 处理成功后设置 `orders.auto_routed_to_scm = True`

### 4. create_printify_orders_from_scm (scm_orders 表 → Printify API)
- **检查标志**: `scm_orders.auto_created_printify_order == False`
- **设置标志**: 处理成功后设置 `scm_orders.auto_created_printify_order = True`

### 5. sync_printify_orders_to_local (Printify API → printify_orders 表)
- **检查标志**: `printify_orders.auto_synced_from_api == False`（主要用于标记，此任务每次都会更新）
- **设置标志**: 处理成功后设置 `printify_orders.auto_synced_from_api = True`

### 6. sync_fulfillment_status (printify_orders 表 → scm_orders 表)
- **检查标志**: `printify_orders.auto_synced_fulfillment_to_scm == False`
- **设置标志**: 
  - `printify_orders.auto_synced_fulfillment_to_scm = True`
  - `scm_orders.auto_synced_fulfillment_from_printify = True`

### 7. sync_to_external_fulfillment (scm_orders 表 → Shopify API)
- **检查标志**: `scm_orders.auto_synced_fulfillment_to_shopify == False`
- **设置标志**: 处理成功后设置 `scm_orders.auto_synced_fulfillment_to_shopify = True`

### 8. sync_shopify_fulfillment_to_local (Shopify API → shopify_orders 表)
- **检查标志**: `shopify_orders.auto_synced_fulfillment_from_api == False`
- **设置标志**: 处理成功后设置 `shopify_orders.auto_synced_fulfillment_from_api = True`

### 9. sync_shopify_local_fulfillment_to_core (shopify_orders 表 → orders 表)
- **检查标志**: `shopify_orders.auto_synced_fulfillment_to_core == False`
- **设置标志**: 处理成功后设置 `shopify_orders.auto_synced_fulfillment_to_core = True`

## 手动处理

手动触发和自动触发使用相同的标志检查逻辑，默认 `ignore_flags=False`，处理过就不再处理。

### API 调用示例

```json
POST /api/v1/automation/configs/{step_key}/trigger
{
  "ignore_flags": false,  // 默认值，处理过就不再处理
  "params": {
    "limit": 100
  }
}
```

### 重新处理数据

如果需要重新处理某些数据，需要先重置标志：

1. **在画面上操作**：通过画面上的功能重置标志（具体功能待实现）
2. **直接更新数据库**：将对应记录的标志字段设置为 `FALSE`，然后再触发任务

```sql
-- 重置 shopify_orders 表的标志
UPDATE shopify_orders SET auto_synced_to_core = FALSE WHERE id = ?;

-- 重置 orders 表的标志
UPDATE orders SET auto_routed_to_scm = FALSE WHERE id = ?;

-- 重置 scm_orders 表的标志
UPDATE scm_orders SET auto_created_printify_order = FALSE WHERE id = ?;
UPDATE scm_orders SET auto_synced_fulfillment_to_shopify = FALSE WHERE id = ?;

-- 重置 printify_orders 表的标志
UPDATE printify_orders SET auto_synced_from_api = FALSE WHERE id = ?;
UPDATE printify_orders SET auto_synced_fulfillment_to_scm = FALSE WHERE id = ?;
```

## 数据库迁移

运行迁移脚本添加标志字段：

```bash
cd backend
python scripts/add_auto_processed_flags.py
```

## 注意事项

1. **默认值**: 所有标志字段默认值为 `FALSE`，表示未处理
2. **自动任务**: 只处理标志为 `FALSE` 的数据
3. **手动触发**: 与自动触发相同，默认也只处理标志为 `FALSE` 的数据
4. **标志设置**: 处理成功后自动设置标志为 `TRUE`，无论手动还是自动触发
5. **重新处理**: 如需重新处理，需要先在画面上重置标志为 `FALSE`，然后再触发任务
6. **索引**: 所有标志字段都创建了索引，提高查询性能
