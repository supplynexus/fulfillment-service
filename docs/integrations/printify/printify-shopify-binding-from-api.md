# Printify ↔ Shopify 绑定：用 API 返回值自动建立（无需仅靠手动映射）

## 结论（先看）

**可以**用 Printify API 返回 + Shopify 商品 API 建立「Printify 商品/变体 ↔ Shopify 商品/变体」的绑定，从而减少或替代「核心商品 ↔ Printify」的手动映射。

- **商品级**：Printify 已发布到 Shopify 时，API 返回里有 **`external.id` = Shopify 商品 ID**，可直接用。
- **变体级**：Printify API **未**在 variant 上返回 Shopify variant id；需用 **Shopify 商品 API** 按 product id 拉取 variants，再按 **options（如 color/size）** 与 Printify 的 variants 匹配，建立 Printify variant id ↔ Shopify variant id。

---

## 1. Printify API 实际返回（已用本地 JSON 验证）

数据来源：项目内 `scripts/printify_product_6978c01e1868fbefd300e159.json`（单商品完整响应）。

### 1.1 商品级：`external`（Shopify 绑定）

当商品在 Printify 里 **Publish 到 Shopify** 后，根级别会有 `external`：

```json
{
  "external": {
    "id": "8411387199588",
    "handle": "https://x0ri77-4v.myshopify.com/products/no-ice-lemonade-unisex-softstyle-t-shirt",
    "shipping_template_id": "101770264676",
    "type": 1
  }
}
```

| 字段 | 含义 | 用途 |
|------|------|------|
| `external.id` | **Shopify 商品 ID**（与 Shopify Admin API 的 product id 一致） | 直接用作「Printify product ↔ Shopify product」绑定 |
| `external.handle` | Shopify 商品 URL | 可解析出 `handle`（如 `no-ice-lemonade-unisex-softstyle-t-shirt`） |

因此：

- **Printify product id** = 响应根级 `id`（如 `"6978c01e1868fbefd300e159"`）
- **Shopify product id** = `external.id`（如 `"8411387199588"`）

商品级绑定无需额外接口，用 Printify 单商品接口（或列表里每条 `raw_data`）即可。

### 1.2 商品级：`sales_channel_properties`

当前样本里只有渠道级配置，没有更多 Shopify 侧 ID：

```json
"sales_channel_properties": {
  "collections": ["313532153956"],
  "free_shipping": false
}
```

不能从这里拿 Shopify product/variant id，以 `external` 为准即可。

### 1.3 变体级：无 Shopify variant id

`variants[]` 中每个元素示例：

```json
{
  "id": 63300,
  "sku": "34466904991495969556",
  "cost": 2180,
  "price": 2499,
  "title": "Dark Heather / L",
  "options": { "color": "Dark Heather", "size": "L" },
  ...
}
```

- `id`：Printify variant id（整数）
- `sku`：由 Printify/渠道生成，**未在文档中承诺为 Shopify variant id**
- **没有** `external_id` / `shopify_variant_id` 等字段

因此变体级不能只靠 Printify 单商品 API 得到 Shopify variant id，需要配合 Shopify 商品 API。

---

## 2. 用「Printify API + Shopify 商品 API」建立绑定的做法

### 2.1 商品级（可直接用）

1. 拉取 Printify 商品（单商品或列表中的 `raw_data`）。
2. 若 `raw_data.external` 存在且 `raw_data.external.id` 非空：
   - **Printify product id** = `raw_data.id`
   - **Shopify product id** = `raw_data.external.id`
3. 可选：用 Shopify 商品 API 以 `external.id` 拉取该商品详情，做校验或补全 handle 等信息。

这样即可得到「Printify product id ↔ Shopify product id」的绑定表（或写入你现有的 mapping 表），无需用户在手 mapping 页为「核心商品 ↔ Printify」逐个绑定。

### 2.2 变体级（options 匹配）

1. 用上面得到的 **Shopify product id** 调 **Shopify 商品 API**（GraphQL 或 REST）拉取该商品的 variants。
2. Shopify 每个 variant 有：
   - `id`（Shopify variant id）
   - `selectedOptions` / option 组合（如 `[{ name: "Color", value: "Dark Heather" }, { name: "Size", value: "L" }]`）
3. Printify 的 `variants[]` 有 `options`（如 `{ "color": "Dark Heather", "size": "L" }`）。
4. 对每个 Printify variant，用 **options 规范化后匹配** Shopify variant（option 名/值一致或做简单归一化），建立：
   - **Printify variant id**（`variants[].id`）↔ **Shopify variant id**

注意：

- option 名称可能不完全一致（如 Color vs color），建议做大小写/空格归一化。
- 若存在多选项顺序不同，需统一排序后再比较。

---

## 3. 和当前「核心商品 + 手动 Printify 映射」的关系

- **现有流程**：Shopify 订单 → 解析出 core_variant_id / core_product_id → 查 **product_mappings（核心 ↔ Printify）** → 得到 Printify product_id / variant_id → 调 Printify 下单。
- **若改用 API 绑定**：
  - 可以增加一条链路：**Shopify product id / variant id**（来自订单）→ 用「Printify API 的 external + Shopify 商品 API」解析出 **Printify product id / variant id** → 调 Printify 下单。
  - 这样**不依赖**「核心商品 ↔ Printify」的映射，适合「订单来自 Shopify、且商品是 Printify Publish 过去」的场景。
- 若仍保留核心商品体系，也可以：
  - 用「Printify API + Shopify API」自动生成或补全 **product_mappings**（例如 core 商品来自 Shopify 同步时已有 Shopify product/variant id，再与 Printify 的 external + options 匹配），减少在手 mapping 页的手动绑定。

---

## 4. 实现时建议

1. **读 Printify 数据**：优先用已落库的 `PrintifyProduct.raw_data`（或实时调 `GET /v1/shops/{shop_id}/products/{product_id}.json`），取 `raw_data.external`、`raw_data.variants`。
2. **商品级**：`external.id` 存在即视为已发布到 Shopify，且即 Shopify product id；可写进配置表或 mapping 表（例如 `external_product_id` = Printify id，再存一列 `shopify_product_id` = `external.id`）。
3. **变体级**：实现一个「按 Shopify product id 拉取 Shopify variants + 与 Printify variants 按 options 匹配」的辅助函数，输出 (Printify variant id, Shopify variant id) 对；订单里若只有 Shopify variant id，可先用该表反查 Printify variant id 再下单。
4. **兼容**：与现有「核心商品 ↔ Printify」映射并存，通过配置或路由决定某订单走「核心+映射」还是「Shopify id → API 绑定 → Printify id」。

---

## 5. 参考

- Printify 单商品 API：`GET https://api.printify.com/v1/shops/{shop_id}/products/{product_id}.json`
- 本地样本：`scripts/printify_product_6978c01e1868fbefd300e159.json`
- 后端已存：`PrintifyProduct.raw_data`、`ExternalProduct.external_data` 中即上述结构

---

## 6. Impeach 租户本地数据库审计（2026-02-11）

基于本地库只读查询，结论如下。

### 6.1 租户与 Key

| 项目 | 值 |
|------|-----|
| 租户 | **impeach**（tenant_id = 1, display_name = Impeach Store） |
| Shopify 外部系统 | id=1, name=Impeach Shopify Store, external_system_id=x0ri77-4v, base_url=https://x0ri77-4v.myshopify.com，**credentials 已配置** |
| Printify 外部系统 | id=4, name=Impeach Printify Store, external_system_id=21704929，**credentials 已配置** |

（未在文档中写入具体 key 内容；仅确认存在且为 object。）

### 6.2 Shopify 商品与数据库

- **核心商品（products）**：42 条（tenant_id=1）。核心表上 `external_system_id` 均为 NULL，来源关系在映射表。
- **product_mappings（Shopify）**：596 条（external_system_id=1），覆盖 42 个核心商品（每商品多条为变体级映射）。
- **external_products（Shopify）**：42 条，`external_product_id` 为 `gid://shopify/Product/xxxx`，**均有 external_data**（商品详情 JSON 已落库）。
- **结论**：Shopify 商品列表/详情已通过「核心商品 + product_mappings + external_products」与数据库一致绑定；核心商品与 Shopify 的绑定正确（抽样：core 标题与 external_products.title 一致，external_product_id 一致）。

### 6.3 Printify 商品与数据库

- **printify_products**：208 条（tenant_id=1, external_system_id=4），均有 **raw_data**（即 Printify API 商品详情 JSON 已落库）。
- 其中 **42 条** 的 `raw_data.external` 存在（即已发布到 Shopify）。
- **product_mappings（Printify）**：214 条（external_system_id=4），覆盖 **16 个**核心商品。
- **结论**：Printify 商品列表/详情已在库；手动绑定的 16 个核心商品与 Printify 的映射正确——抽样校验显示，同一核心商品的 Shopify `external_product_id`（gid 中的数字）与 Printify `raw_data.external.id` 一致（binding_ok=match）。

### 6.4 核心 ↔ Shopify ↔ Printify 一致性

对「既有 Shopify 映射又有 Printify 映射」的核心商品做了抽样：Printify 的 `raw_data.external.id` 与 product_mappings 中 Shopify 的 `external_product_id`（gid 数字部分）一致，说明**当前手动绑定正确**，与 Printify API 返回的 Shopify 绑定一致。

### 6.5 未绑定 Printify 的核心商品

- 42 个核心商品均有 Shopify 映射；其中 **26 个**尚无 Printify 映射。
- 这 26 个里，**25 个**在本地 printify_products 中能找到「已发布到 Shopify」的对应商品（即 `raw_data.external.id` = 该核心商品在 Shopify 映射里的 product id）。
- **1 个**（core_product_id=99, IMPEACH BASIC BLACK）在 Printify 库中无 matching external.id，可能非 Printify 发布或未发布到该店铺。

### 6.6 小结表

| 项目 | 数量/说明 |
|------|------------|
| 核心商品 | 42 |
| 核心–Shopify 映射（条） | 596（42 商品 × 变体） |
| 核心–Printify 映射（条） | 214（16 商品 × 变体） |
| external_products（Shopify） | 42，均有 external_data |
| printify_products | 208，42 条含 raw_data.external |
| 可自动绑定（按 external.id 匹配） | **25 个核心商品** |

---

## 7. 批处理自动绑定剩余商品

### 7.1 思路

对「有 Shopify 映射、无 Printify 映射」的核心商品，若在 **printify_products** 中存在 `raw_data.external.id` = 该核心在 Shopify 的 product id（gid 数字部分），则可为该核心商品与对应 Printify 商品建立 **product_mappings**（商品级 + 变体级）。

- **商品级**：插入 `tenant_id=1, core_product_id, external_system_id=4, external_product_id=printify_product_id, core_variant_id=NULL, external_variant_id=NULL`（若业务允许商品级映射）。
- **变体级**：按文档 2.2，用 Shopify 商品 API 拉取该 product 的 variants，与 Printify `raw_data.variants` 按 options 匹配，为每个 core_variant 插入一条 mapping（core_variant_id, external_variant_id=Printify variant id）。

### 7.2 已实现：API 自动绑定（商品级）

后端已提供接口，**无需再写脚本**即可预览或执行绑定：

- **接口**：`POST /api/v1/products/mappings/auto-bind-printify-by-shopify`
- **鉴权**：需租户登录（与现有商品映射 API 一致）。
- **查询参数**：
  - `dry_run`：`true`（默认）= 仅预览，返回候选列表不写入；`false` = 实际创建映射。
- **响应**：
  - `dry_run`：是否仅为预览。
  - `candidates`：数组，每项 `{ core_product_id, core_title, printify_product_id, printify_title, shopify_product_id }`。
  - `created_count`：本次创建的映射条数（仅当 `dry_run=false` 时 >0）。
  - `skipped_already_mapped`：已存在 Printify 映射而跳过的数量。
  - `error`：错误信息（若有）。

**使用步骤：**

1. **先预览**（推荐）  
   ```bash
   curl -X POST "http://localhost:8000/api/v1/products/mappings/auto-bind-printify-by-shopify?dry_run=true" \
     -H "Authorization: Bearer <租户 token>" \
     -H "Content-Type: application/json"
   ```  
   查看返回的 `candidates` 是否符合预期。

2. **再执行**  
   ```bash
   curl -X POST "http://localhost:8000/api/v1/products/mappings/auto-bind-printify-by-shopify?dry_run=false" \
     -H "Authorization: Bearer <租户 token>" \
     -H "Content-Type: application/json"
   ```  
   查看 `created_count` 与 `skipped_already_mapped`。

逻辑说明：  
- 仅处理「有 Shopify 映射、无 Printify 映射」的核心商品。  
- 用其 Shopify `external_product_id`（gid 数字部分）与 `printify_products.raw_data.external.id` 匹配。  
- 每个匹配创建**一条商品级** `product_mappings`（`core_variant_id`/`external_variant_id` 为空）；下单时走现有「商品级映射 + SKU/options 回退」即可。

**自动化管理中的绑定步骤（推荐）**

同一逻辑已接入 **系统设置 → 自动化管理**（`/automation`），在「商品同步」分类下：

- **步骤名称**：Printify–Shopify 商品自动绑定  
- **说明**：按 Printify raw_data.external.id 与核心商品 Shopify 映射匹配，为「有 Shopify、无 Printify」的核心商品自动创建商品级映射。建议在「Printify 商品同步到本地」之后运行。  
- **默认调度**：每日 0:05、12:05（略晚于商品同步 0:00、12:00）。  
- 可在该页**启用/禁用**、**配置 cron**、或点击**播放按钮**手动触发，无需调用 API 或跑脚本。

### 7.3 变体级补全（可选）

- 对已绑定的商品，若需变体级映射：用 Shopify 商品 API 拉取 variants，与 Printify `raw_data.variants` 按 options 匹配，为每个 core_variant 写入一条带 `core_variant_id` + `external_variant_id` 的 mapping。  
- 需注意：option 名/值归一化、多选项顺序、以及幂等（已存在则跳过）。当前 API 仅做商品级，变体级尚未实现。
