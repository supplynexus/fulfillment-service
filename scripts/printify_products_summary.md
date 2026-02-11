# Printify 店铺商品汇总报告

生成时间: 2025-02-01

## 店铺列表

### 店铺 1
- **店铺 ID**: 21704929
- **店铺名称**: IMPEACH
- **商品总数**: 69
- **主要商品系列**: VOX POPULI Collection（交互式投票系列）
- **商品文件**: `printify_products_shop1.json` (15MB)

### 店铺 2
- **店铺 ID**: 24981565
- **店铺名称**: IMPEACH
- **商品总数**: 70
- **主要商品系列**: THE BREACH Collection, TEST11111
- **商品文件**: `printify_products_shop2.json` (15MB)

## 商品详情

### 店铺 1 (ID: 21704929) - 前 10 个商品

1. "Most Lying?" Interactive Poll Hoodie | VOX POPULI Collection
2. "Most Dictatorial?" Interactive Poll Hoodie | VOX POPULI Collection
3. "Most Corrupt?" Interactive Poll Hoodie | VOX POPULI Collection
4. "Least Qualified?" Interactive Poll Hoodie | VOX POPULI Collection
5. President's Day Limited Drop | JFK "Rights of Every Man"
6. President's Day Limited Drop | Ronald Reagan "Freedom is Fragile"

### 店铺 2 (ID: 24981565) - 前 10 个商品

1. TEST11111
2. "Lose My Job" Statement Tee | THE BREACH Collection
3. "Kid's Tuition" Statement Tee | THE BREACH Collection
4. "Nonstop Lie" Statement Tee | THE BREACH Collection
5. "Priced Out" Groceries Statement | THE BREACH Collection
6. "Stupid Tariffs" Statement Tee | THE BREACH Collection

## 使用说明

### 查看完整商品列表

```bash
# 查看店铺 1 的商品
cat printify_products_shop1.json | python -m json.tool | less

# 查看店铺 2 的商品
cat printify_products_shop2.json | python -m json.tool | less
```

### 统计信息

```bash
# 统计可见商品数量
python -c "
import json
with open('printify_products_shop1.json') as f:
    data = json.load(f)
    visible = [p for p in data['products'] if p.get('is_visible', False)]
    print(f'店铺 1 - 可见商品: {len(visible)} / {len(data[\"products\"])}')

with open('printify_products_shop2.json') as f:
    data = json.load(f)
    visible = [p for p in data['products'] if p.get('is_visible', False)]
    print(f'店铺 2 - 可见商品: {len(visible)} / {len(data[\"products\"])}')
"
```

## 注意事项

- 两个店铺都叫 "IMPEACH"
- 需要根据 Printify 界面中的绿色标识来确定哪个是绿色店铺
- 所有商品数据已保存为 JSON 文件，可以进一步分析
