#!/usr/bin/env python3
"""
基于 SKU（Color + Size）进行变体级别的商品映射

使用方法:
  python scripts/map_variants_by_sku.py --tenant impeach

功能:
1. 读取 Printify 和 Shopify 商品数据
2. 先进行商品级别的匹配（基于标题）
3. 对于每个匹配的商品对，展开所有变体组合
4. 匹配变体（基于 Color + Size）
5. 标记哪些变体在 Printify 上不能销售（is_enabled=false 或 is_available=false）
6. 生成详细的 CSV 报告
"""

import json
import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set


def normalize_title(title: str) -> str:
    """标准化商品标题，用于匹配"""
    if not title:
        return ""
    normalized = title.lower().strip()
    normalized = "".join(c if c.isalnum() or c.isspace() else " " for c in normalized)
    normalized = " ".join(normalized.split())
    return normalized


def match_products_by_title(
    printify_products: List[Dict],
    shopify_products: List[Dict]
) -> List[Dict]:
    """基于标题匹配商品"""
    matched_pairs = []
    matched_shopify_ids = set()
    
    for printify_product in printify_products:
        printify_title = printify_product.get("title", "")
        printify_normalized = normalize_title(printify_title)
        
        for shopify_product in shopify_products:
            shopify_id = shopify_product.get("id", "")
            if shopify_id in matched_shopify_ids:
                continue
                
            shopify_title = shopify_product.get("title", "")
            shopify_normalized = normalize_title(shopify_title)
            
            if printify_normalized == shopify_normalized:
                matched_pairs.append({
                    "printify": printify_product,
                    "shopify": shopify_product,
                })
                matched_shopify_ids.add(shopify_id)
                break
    
    return matched_pairs


def get_printify_variant_color_size(printify_variant: Dict, printify_options: List[Dict]) -> Tuple[Optional[str], Optional[str]]:
    """从 Printify 变体中提取颜色和尺寸"""
    variant_options = printify_variant.get("options", [])
    if not variant_options or len(variant_options) < 2:
        return None, None
    
    # Printify 变体的 options 是 ID 数组
    # 注意：顺序可能是 [size_id, color_id] 或 [color_id, size_id]
    # 需要根据 options 的类型来判断
    size_id = None
    color_id = None
    
    # 先找出哪个是尺寸，哪个是颜色
    for option in printify_options:
        option_name = option.get("name", "").lower()
        option_type = option.get("type", "").lower()
        option_values = option.get("values", [])
        
        if (option_name == "sizes" or option_name == "size") and option_type == "size":
            # 这是尺寸选项
            for value in option_values:
                value_id = value.get("id")
                if value_id in variant_options:
                    size_id = value_id
                    break
        elif (option_name == "colors" or option_name == "color") and option_type == "color":
            # 这是颜色选项
            for value in option_values:
                value_id = value.get("id")
                if value_id in variant_options:
                    color_id = value_id
                    break
    
    # 如果没找到，尝试从变体标题中提取（格式通常是 "Color / Size"）
    color_name = None
    size_name = None
    
    if size_id:
        for option in printify_options:
            if (option.get("name", "").lower() == "sizes" or option.get("name", "").lower() == "size"):
                for value in option.get("values", []):
                    if value.get("id") == size_id:
                        size_name = value.get("title")
                        break
    
    if color_id:
        for option in printify_options:
            if option.get("type", "").lower() == "color":
                for value in option.get("values", []):
                    if value.get("id") == color_id:
                        color_name = value.get("title")
                        break
    
    # 如果还是没找到，尝试从变体标题解析（格式通常是 "Color / Size"）
    if not color_name or not size_name:
        variant_title = printify_variant.get("title", "")
        if " / " in variant_title:
            parts = variant_title.split(" / ")
            if len(parts) == 2:
                if not color_name:
                    color_name = parts[0].strip()
                if not size_name:
                    size_name = parts[1].strip()
    
    return color_name, size_name


def get_shopify_variant_color_size(shopify_variant: Dict) -> Tuple[Optional[str], Optional[str]]:
    """从 Shopify 变体中提取颜色和尺寸"""
    selected_options = shopify_variant.get("selectedOptions", [])
    color_name = None
    size_name = None
    
    for option in selected_options:
        name = option.get("name", "").lower()
        value = option.get("value", "")
        if name == "color":
            color_name = value
        elif name == "size":
            size_name = value
    
    return color_name, size_name


def normalize_color_size(color: Optional[str], size: Optional[str]) -> str:
    """标准化颜色和尺寸组合，用于匹配"""
    color_str = (color or "").strip().lower()
    size_str = (size or "").strip().lower()
    return f"{color_str}|{size_str}"


def match_variants(
    printify_product: Dict,
    shopify_product: Dict
) -> List[Dict]:
    """匹配商品的变体"""
    printify_variants = printify_product.get("variants", [])
    shopify_variants = shopify_product.get("variants", {}).get("nodes", [])
    printify_options = printify_product.get("options", [])
    
    # 构建 Printify 变体映射（color+size -> variant）
    printify_variant_map = {}
    for variant in printify_variants:
        color, size = get_printify_variant_color_size(variant, printify_options)
        if color and size:
            key = normalize_color_size(color, size)
            printify_variant_map[key] = variant
    
    # 匹配 Shopify 变体
    matched_variants = []
    matched_printify_keys = set()
    
    for shopify_variant in shopify_variants:
        shopify_color, shopify_size = get_shopify_variant_color_size(shopify_variant)
        if not shopify_color or not shopify_size:
            # 无法提取颜色或尺寸，标记为未匹配
            matched_variants.append({
                "status": "❌ 无法匹配（缺少颜色或尺寸信息）",
                "shopify_variant": shopify_variant,
                "printify_variant": None,
                "color": shopify_color,
                "size": shopify_size,
            })
            continue
        
        key = normalize_color_size(shopify_color, shopify_size)
        printify_variant = printify_variant_map.get(key)
        
        if printify_variant:
            # 检查 Printify 变体是否可以销售
            is_enabled = printify_variant.get("is_enabled", False)
            is_available = printify_variant.get("is_available", True)
            can_sell = is_enabled and is_available
            
            status = "✅ 已匹配"
            if not can_sell:
                status = "⚠️ 已匹配但 Printify 不可销售"
            
            matched_variants.append({
                "status": status,
                "shopify_variant": shopify_variant,
                "printify_variant": printify_variant,
                "color": shopify_color,
                "size": shopify_size,
                "printify_is_enabled": is_enabled,
                "printify_is_available": is_available,
                "can_sell_on_printify": can_sell,
            })
            matched_printify_keys.add(key)
        else:
            # Printify 中没有对应的变体
            matched_variants.append({
                "status": "❌ Printify 无此变体",
                "shopify_variant": shopify_variant,
                "printify_variant": None,
                "color": shopify_color,
                "size": shopify_size,
            })
    
    # 找出 Printify 中有但 Shopify 中没有的变体
    for key, printify_variant in printify_variant_map.items():
        if key not in matched_printify_keys:
            color, size = get_printify_variant_color_size(printify_variant, printify_options)
            is_enabled = printify_variant.get("is_enabled", False)
            is_available = printify_variant.get("is_available", True)
            can_sell = is_enabled and is_available
            
            status = "❌ Shopify 无此变体"
            if not can_sell:
                status = "❌ Shopify 无此变体（Printify 不可销售）"
            
            matched_variants.append({
                "status": status,
                "shopify_variant": None,
                "printify_variant": printify_variant,
                "color": color,
                "size": size,
                "printify_is_enabled": is_enabled,
                "printify_is_available": is_available,
                "can_sell_on_printify": can_sell,
            })
    
    return matched_variants


def export_to_csv(matched_products: List[Dict], output_file: Path):
    """导出变体匹配结果到 CSV"""
    fieldnames = [
        "商品匹配状态",
        "Printify 商品ID",
        "Printify 商品标题",
        "Shopify 商品ID",
        "Shopify 商品标题",
        "变体匹配状态",
        "颜色",
        "尺寸",
        "Shopify 变体ID",
        "Shopify 变体标题",
        "Shopify SKU",
        "Shopify 价格",
        "Shopify 库存",
        "Printify 变体ID",
        "Printify 变体标题",
        "Printify SKU",
        "Printify 价格",
        "Printify 成本",
        "Printify is_enabled",
        "Printify is_available",
        "Printify 可销售",
    ]
    
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for product_pair in matched_products:
            printify_product = product_pair["printify"]
            shopify_product = product_pair["shopify"]
            variants = product_pair["variants"]
            
            for variant_match in variants:
                shopify_variant = variant_match.get("shopify_variant")
                printify_variant = variant_match.get("printify_variant")
                
                row = {
                    "商品匹配状态": "✅ 商品已匹配",
                    "Printify 商品ID": printify_product.get("id", ""),
                    "Printify 商品标题": printify_product.get("title", ""),
                    "Shopify 商品ID": shopify_product.get("id", ""),
                    "Shopify 商品标题": shopify_product.get("title", ""),
                    "变体匹配状态": variant_match.get("status", ""),
                    "颜色": variant_match.get("color", ""),
                    "尺寸": variant_match.get("size", ""),
                }
                
                # Shopify 变体信息
                if shopify_variant:
                    row.update({
                        "Shopify 变体ID": shopify_variant.get("id", ""),
                        "Shopify 变体标题": shopify_variant.get("title", ""),
                        "Shopify SKU": shopify_variant.get("sku", ""),
                        "Shopify 价格": shopify_variant.get("price", ""),
                        "Shopify 库存": shopify_variant.get("inventoryQuantity", 0),
                    })
                else:
                    row.update({
                        "Shopify 变体ID": "",
                        "Shopify 变体标题": "",
                        "Shopify SKU": "",
                        "Shopify 价格": "",
                        "Shopify 库存": "",
                    })
                
                # Printify 变体信息
                if printify_variant:
                    row.update({
                        "Printify 变体ID": printify_variant.get("id", ""),
                        "Printify 变体标题": printify_variant.get("title", ""),
                        "Printify SKU": printify_variant.get("sku", ""),
                        "Printify 价格": f"{printify_variant.get('price', 0) / 100:.2f}" if printify_variant.get("price") else "",
                        "Printify 成本": f"{printify_variant.get('cost', 0) / 100:.2f}" if printify_variant.get("cost") else "",
                        "Printify is_enabled": "是" if printify_variant.get("is_enabled") else "否",
                        "Printify is_available": "是" if printify_variant.get("is_available") else "否",
                        "Printify 可销售": "是" if variant_match.get("can_sell_on_printify", False) else "否",
                    })
                else:
                    row.update({
                        "Printify 变体ID": "",
                        "Printify 变体标题": "",
                        "Printify SKU": "",
                        "Printify 价格": "",
                        "Printify 成本": "",
                        "Printify is_enabled": "",
                        "Printify is_available": "",
                        "Printify 可销售": "",
                    })
                
                writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="基于 SKU（Color + Size）进行变体级别的商品映射")
    parser.add_argument("--tenant", help="指定租户名称")
    parser.add_argument("--printify-file", default="green_store_products.json", help="Printify 商品 JSON 文件")
    parser.add_argument("--shopify-file", default="shopify_store_products.json", help="Shopify 商品 JSON 文件")
    parser.add_argument("--output", default="variant_mapping.csv", help="输出 CSV 文件路径")
    args = parser.parse_args()
    
    # 读取 Printify 商品
    printify_file = Path(args.printify_file)
    if not printify_file.exists():
        print(f"❌ Printify 商品文件不存在: {printify_file}")
        return
    
    print(f"📖 读取 Printify 商品: {printify_file}")
    with open(printify_file, "r", encoding="utf-8") as f:
        printify_data = json.load(f)
    
    printify_products = printify_data.get("products", [])
    print(f"   ✅ 读取 {len(printify_products)} 个 Printify 商品")
    
    # 读取 Shopify 商品
    shopify_file = Path(args.shopify_file)
    if not shopify_file.exists():
        print(f"❌ Shopify 商品文件不存在: {shopify_file}")
        return
    
    print(f"📖 读取 Shopify 商品: {shopify_file}")
    with open(shopify_file, "r", encoding="utf-8") as f:
        shopify_data = json.load(f)
    
    shopify_products = shopify_data.get("products", [])
    print(f"   ✅ 读取 {len(shopify_products)} 个 Shopify 商品")
    print()
    
    # 步骤 1: 商品级别匹配
    print("=" * 80)
    print("步骤 1: 商品级别匹配（基于标题）")
    print("=" * 80)
    matched_products = match_products_by_title(printify_products, shopify_products)
    print(f"✅ 匹配到 {len(matched_products)} 对商品")
    print()
    
    # 步骤 2: 变体级别匹配
    print("=" * 80)
    print("步骤 2: 变体级别匹配（基于 Color + Size）")
    print("=" * 80)
    
    total_variants = 0
    matched_sellable_count = 0  # 匹配且可销售
    matched_not_sellable_count = 0  # 匹配但不可销售
    unmapped_shopify_variants = 0
    unmapped_printify_variants = 0
    
    for i, product_pair in enumerate(matched_products, 1):
        printify_product = product_pair["printify"]
        shopify_product = product_pair["shopify"]
        
        print(f"\n[{i}/{len(matched_products)}] {printify_product.get('title', '')[:60]}...")
        
        variants = match_variants(printify_product, shopify_product)
        product_pair["variants"] = variants
        total_variants += len(variants)
        
        for variant_match in variants:
            status = variant_match.get("status", "")
            if "✅" in status:
                matched_sellable_count += 1
            elif "⚠️" in status:
                matched_not_sellable_count += 1
            elif "❌ Printify 无此变体" in status:
                unmapped_shopify_variants += 1
            elif "❌ Shopify 无此变体" in status:
                unmapped_printify_variants += 1
    
    total_matched = matched_sellable_count + matched_not_sellable_count
    
    print()
    print("=" * 80)
    print("变体匹配统计")
    print("=" * 80)
    print(f"总变体数: {total_variants}")
    print(f"✅ 已匹配且可销售: {matched_sellable_count}")
    print(f"⚠️ 已匹配但 Printify 不可销售: {matched_not_sellable_count}")
    print(f"   总匹配数（可销售 + 不可销售）: {total_matched}")
    print(f"❌ Shopify 变体在 Printify 中不存在: {unmapped_shopify_variants}")
    print(f"❌ Printify 变体在 Shopify 中不存在: {unmapped_printify_variants}")
    print()
    print("💡 说明:")
    if unmapped_shopify_variants == 0:
        print(f"   ✅ 所有 Shopify 变体都找到了对应的 Printify 变体（匹配率 100%）")
        print(f"   - 其中 {matched_sellable_count} 个可以销售，{matched_not_sellable_count} 个不可销售")
        print(f"   - 不可销售的原因：is_enabled=false 或 is_available=false")
    else:
        print(f"   ⚠️ 有 {unmapped_shopify_variants} 个 Shopify 变体在 Printify 中不存在")
        print(f"   - 已匹配: {total_matched} 个（{matched_sellable_count} 可销售，{matched_not_sellable_count} 不可销售）")
    print()
    
    # 导出 CSV
    output_file = Path(args.output)
    print(f"📝 导出 CSV 文件: {output_file}")
    export_to_csv(matched_products, output_file)
    print(f"✅ CSV 文件已导出: {output_file}")
    print()
    print("💡 提示:")
    print(f"   - 可以在 Excel 或 Pages 中打开: {output_file}")
    print(f"   - 使用筛选功能可以快速查看:")
    print(f"     * 筛选 '变体匹配状态' = '⚠️ 已匹配但 Printify 不可销售' 查看不能销售的变体")
    print(f"     * 筛选 '变体匹配状态' = '❌ Printify 无此变体' 查看 Shopify 独有的变体")
    print(f"     * 筛选 '变体匹配状态' = '❌ Shopify 无此变体' 查看 Printify 独有的变体")


if __name__ == "__main__":
    main()
