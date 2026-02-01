#!/usr/bin/env python3
"""
映射 Printify 和 Shopify 商品

使用方法:
   python scripts/map_printify_shopify_products.py --tenant impeach

功能:
1. 读取 Printify 商品数据 (green_store_products.json)
2. 读取 Shopify 商品数据 (shopify_store_products.json)
3. 尝试匹配商品（通过标题、SKU等）
4. 报告无法映射的商品
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))


def normalize_title(title: str) -> str:
    """标准化商品标题，用于匹配"""
    if not title:
        return ""
    # 转换为小写，移除多余空格
    normalized = title.lower().strip()
    # 移除特殊字符，只保留字母数字和空格
    normalized = "".join(c if c.isalnum() or c.isspace() else " " for c in normalized)
    # 合并多个空格
    normalized = " ".join(normalized.split())
    return normalized


def calculate_similarity(str1: str, str2: str) -> float:
    """计算两个字符串的相似度（0-1）"""
    return SequenceMatcher(None, normalize_title(str1), normalize_title(str2)).ratio()


def extract_keywords(title: str) -> set:
    """提取标题中的关键词"""
    if not title:
        return set()
    normalized = normalize_title(title)
    # 移除常见的停用词
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
    words = set(normalized.split())
    return words - stop_words


def match_products(
    printify_products: List[Dict],
    shopify_products: List[Dict]
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    匹配 Printify 和 Shopify 商品
    
    返回:
        (matched_pairs, unmatched_printify, unmatched_shopify)
    """
    matched_pairs = []
    matched_printify_ids = set()
    matched_shopify_ids = set()
    
    # 第一轮：精确匹配（标题完全一致）
    print("🔍 第一轮匹配：精确标题匹配...")
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
                    "match_type": "exact_title",
                    "similarity": 1.0
                })
                matched_printify_ids.add(printify_product.get("id"))
                matched_shopify_ids.add(shopify_id)
                break
    
    print(f"   ✅ 精确匹配: {len(matched_pairs)} 对")
    
    # 第二轮：高相似度匹配（相似度 >= 0.8）
    print("🔍 第二轮匹配：高相似度匹配（相似度 >= 0.8）...")
    for printify_product in printify_products:
        printify_id = printify_product.get("id", "")
        if printify_id in matched_printify_ids:
            continue
            
        printify_title = printify_product.get("title", "")
        best_match = None
        best_similarity = 0.0
        
        for shopify_product in shopify_products:
            shopify_id = shopify_product.get("id", "")
            if shopify_id in matched_shopify_ids:
                continue
                
            shopify_title = shopify_product.get("title", "")
            similarity = calculate_similarity(printify_title, shopify_title)
            
            if similarity >= 0.8 and similarity > best_similarity:
                best_match = shopify_product
                best_similarity = similarity
        
        if best_match:
            matched_pairs.append({
                "printify": printify_product,
                "shopify": best_match,
                "match_type": "high_similarity",
                "similarity": best_similarity
            })
            matched_printify_ids.add(printify_id)
            matched_shopify_ids.add(best_match.get("id"))
    
    print(f"   ✅ 高相似度匹配: {len([p for p in matched_pairs if p['match_type'] == 'high_similarity'])} 对")
    
    # 第三轮：关键词匹配
    print("🔍 第三轮匹配：关键词匹配...")
    for printify_product in printify_products:
        printify_id = printify_product.get("id", "")
        if printify_id in matched_printify_ids:
            continue
            
        printify_title = printify_product.get("title", "")
        printify_keywords = extract_keywords(printify_title)
        
        if not printify_keywords:
            continue
        
        best_match = None
        best_keyword_overlap = 0
        
        for shopify_product in shopify_products:
            shopify_id = shopify_product.get("id", "")
            if shopify_id in matched_shopify_ids:
                continue
                
            shopify_title = shopify_product.get("title", "")
            shopify_keywords = extract_keywords(shopify_title)
            
            # 计算关键词重叠度
            overlap = len(printify_keywords & shopify_keywords)
            total_unique = len(printify_keywords | shopify_keywords)
            
            if total_unique > 0:
                overlap_ratio = overlap / total_unique
                # 如果关键词重叠度 >= 0.6 且至少有 3 个共同关键词
                if overlap_ratio >= 0.6 and overlap >= 3:
                    if overlap > best_keyword_overlap:
                        best_match = shopify_product
                        best_keyword_overlap = overlap
        
        if best_match:
            similarity = calculate_similarity(printify_title, best_match.get("title", ""))
            matched_pairs.append({
                "printify": printify_product,
                "shopify": best_match,
                "match_type": "keyword_match",
                "similarity": similarity,
                "keyword_overlap": best_keyword_overlap
            })
            matched_printify_ids.add(printify_id)
            matched_shopify_ids.add(best_match.get("id"))
    
    print(f"   ✅ 关键词匹配: {len([p for p in matched_pairs if p['match_type'] == 'keyword_match'])} 对")
    
    # 找出未匹配的商品
    unmatched_printify = [
        p for p in printify_products
        if p.get("id") not in matched_printify_ids
    ]
    
    unmatched_shopify = [
        p for p in shopify_products
        if p.get("id") not in matched_shopify_ids
    ]
    
    return matched_pairs, unmatched_printify, unmatched_shopify


def main():
    parser = argparse.ArgumentParser(description="映射 Printify 和 Shopify 商品")
    parser.add_argument("--tenant", help="指定租户名称")
    parser.add_argument("--printify-file", default="green_store_products.json", help="Printify 商品 JSON 文件")
    parser.add_argument("--shopify-file", default="shopify_store_products.json", help="Shopify 商品 JSON 文件")
    parser.add_argument("--output", default="product_mapping.json", help="输出映射结果 JSON 文件")
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
    print("=" * 80)
    print("开始商品映射...")
    print("=" * 80)
    print()
    
    # 执行映射
    matched_pairs, unmatched_printify, unmatched_shopify = match_products(
        printify_products, shopify_products
    )
    
    print()
    print("=" * 80)
    print("映射结果统计")
    print("=" * 80)
    print(f"✅ 成功映射: {len(matched_pairs)} 对")
    print(f"❌ Printify 未映射: {len(unmatched_printify)} 个")
    print(f"❌ Shopify 未映射: {len(unmatched_shopify)} 个")
    print()
    
    # 显示匹配类型统计
    match_type_stats = {}
    for pair in matched_pairs:
        match_type = pair.get("match_type", "unknown")
        match_type_stats[match_type] = match_type_stats.get(match_type, 0) + 1
    
    print("匹配类型统计:")
    for match_type, count in match_type_stats.items():
        print(f"   - {match_type}: {count} 对")
    print()
    
    # 显示未映射的 Printify 商品
    if unmatched_printify:
        print("=" * 80)
        print(f"❌ Printify 未映射商品 ({len(unmatched_printify)} 个)")
        print("=" * 80)
        for i, product in enumerate(unmatched_printify[:20], 1):  # 只显示前20个
            print(f"{i}. {product.get('title', 'N/A')[:80]}")
            print(f"   ID: {product.get('id', 'N/A')}")
            variants_count = len(product.get("variants", []))
            print(f"   变体数: {variants_count}")
            print()
        if len(unmatched_printify) > 20:
            print(f"... 还有 {len(unmatched_printify) - 20} 个未映射商品")
        print()
    
    # 显示未映射的 Shopify 商品
    if unmatched_shopify:
        print("=" * 80)
        print(f"❌ Shopify 未映射商品 ({len(unmatched_shopify)} 个)")
        print("=" * 80)
        for i, product in enumerate(unmatched_shopify[:20], 1):  # 只显示前20个
            print(f"{i}. {product.get('title', 'N/A')[:80]}")
            print(f"   ID: {product.get('id', 'N/A')}")
            variants = product.get("variants", {}).get("nodes", [])
            print(f"   变体数: {len(variants)}")
            print()
        if len(unmatched_shopify) > 20:
            print(f"... 还有 {len(unmatched_shopify) - 20} 个未映射商品")
        print()
    
    # 保存映射结果
    output_data = {
        "summary": {
            "printify_total": len(printify_products),
            "shopify_total": len(shopify_products),
            "matched_count": len(matched_pairs),
            "unmatched_printify_count": len(unmatched_printify),
            "unmatched_shopify_count": len(unmatched_shopify),
            "match_type_stats": match_type_stats
        },
        "matched_pairs": [
            {
                "match_type": pair["match_type"],
                "similarity": pair.get("similarity", 0.0),
                "printify": {
                    "id": pair["printify"].get("id"),
                    "title": pair["printify"].get("title"),
                    "variants_count": len(pair["printify"].get("variants", []))
                },
                "shopify": {
                    "id": pair["shopify"].get("id"),
                    "title": pair["shopify"].get("title"),
                    "handle": pair["shopify"].get("handle"),
                    "variants_count": len(pair["shopify"].get("variants", {}).get("nodes", []))
                }
            }
            for pair in matched_pairs
        ],
        "unmatched_printify": [
            {
                "id": product.get("id"),
                "title": product.get("title"),
                "variants_count": len(product.get("variants", []))
            }
            for product in unmatched_printify
        ],
        "unmatched_shopify": [
            {
                "id": product.get("id"),
                "title": product.get("title"),
                "handle": product.get("handle"),
                "variants_count": len(product.get("variants", {}).get("nodes", []))
            }
            for product in unmatched_shopify
        ]
    }
    
    output_file = Path(args.output)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 映射结果已保存到: {output_file}")
    print()
    print("📊 详细统计:")
    print(f"   Printify 商品总数: {len(printify_products)}")
    print(f"   Shopify 商品总数: {len(shopify_products)}")
    print(f"   成功映射: {len(matched_pairs)} 对 ({len(matched_pairs)/max(len(printify_products), len(shopify_products))*100:.1f}%)")
    print(f"   Printify 未映射: {len(unmatched_printify)} 个 ({len(unmatched_printify)/len(printify_products)*100:.1f}%)")
    print(f"   Shopify 未映射: {len(unmatched_shopify)} 个 ({len(unmatched_shopify)/len(shopify_products)*100:.1f}%)")


if __name__ == "__main__":
    main()
