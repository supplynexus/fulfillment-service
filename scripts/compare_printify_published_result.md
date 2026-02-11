# 三个商品「发布」状态对比（店铺 24981565）

## 已有 JSON 的结论：6978c01e1868fbefd300e159（已发布）

从 `scripts/printify_product_6978c01e1868fbefd300e159.json` 提取的与发布相关字段：

| 字段 | 值 |
|------|-----|
| id | 6978c01e1868fbefd300e159 |
| title | NO ICE \| Lemonade \| Unisex Softstyle T-Shirt |
| **visible** | **true** |
| is_visible | (不存在) |
| **sales_channel_properties** | **dict，非空**，结构如下 |

```json
{
  "collections": ["313532153956"],
  "free_shipping": false
}
```

- 单商品 API 返回的 `sales_channel_properties` 是 **dict**（不是 list），键为 `collections`、`free_shipping` 等。
- **已发布** 时：该 dict **非空**（有 keys），且 `visible === true`。

因此判断「是否已发布」的可靠规则：**`sales_channel_properties` 非空**（list 有元素或 dict 有 key）即视为已发布；空对象/空数组为未发布。当前代码 `_is_published_from_api_data()` 已按此实现。

---

## 如何得到完整对比（含另外两个未发布商品）

本机执行（需替换为你的 Printify API key）：

```bash
PRINTIFY_API_KEY=你的key python scripts/compare_printify_published_three.py
```

脚本会：

1. 拉取三件商品的完整 JSON，并写入：
   - `scripts/printify_product_6978c01e1868fbefd300e159.json`
   - `scripts/printify_product_698254feac45c6e86a0b90b0.json`
   - `scripts/printify_product_69825421562ab484c806a82c.json`
2. 在终端打印三者的「发布相关字段」对比及结论。

预期：两个未发布商品会出现 `visible: false` 和/或 `sales_channel_properties: {}`（或空 list）。
