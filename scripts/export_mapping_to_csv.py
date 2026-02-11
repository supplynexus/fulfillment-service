#!/usr/bin/env python3
"""
将商品映射结果导出为 CSV 格式

使用方法:
  python scripts/export_mapping_to_csv.py --input product_mapping.json --output product_mapping.csv
"""

import json
import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Any


def export_matched_pairs_to_csv(matched_pairs: List[Dict], writer: csv.DictWriter):
    """导出匹配的商品对到 CSV"""
    for pair in matched_pairs:
        printify = pair.get("printify", {})
        shopify = pair.get("shopify", {})
        
        row = {
            "状态": "✅ 已匹配",
            "匹配类型": pair.get("match_type", ""),
            "相似度": f"{pair.get('similarity', 0):.2%}",
            "Printify ID": printify.get("id", ""),
            "Printify 商品标题": printify.get("title", ""),
            "Printify 变体数": printify.get("variants_count", 0),
            "Shopify ID": shopify.get("id", ""),
            "Shopify 商品标题": shopify.get("title", ""),
            "Shopify Handle": shopify.get("handle", ""),
            "Shopify 变体数": shopify.get("variants_count", 0),
        }
        writer.writerow(row)


def export_unmatched_printify_to_csv(unmatched: List[Dict], writer: csv.DictWriter):
    """导出未映射的 Printify 商品到 CSV"""
    for product in unmatched:
        row = {
            "状态": "❌ Printify 未映射",
            "匹配类型": "",
            "相似度": "",
            "Printify ID": product.get("id", ""),
            "Printify 商品标题": product.get("title", ""),
            "Printify 变体数": product.get("variants_count", 0),
            "Shopify ID": "",
            "Shopify 商品标题": "",
            "Shopify Handle": "",
            "Shopify 变体数": "",
        }
        writer.writerow(row)


def export_unmatched_shopify_to_csv(unmatched: List[Dict], writer: csv.DictWriter):
    """导出未映射的 Shopify 商品到 CSV"""
    for product in unmatched:
        row = {
            "状态": "❌ Shopify 未映射",
            "匹配类型": "",
            "相似度": "",
            "Printify ID": "",
            "Printify 商品标题": "",
            "Printify 变体数": "",
            "Shopify ID": product.get("id", ""),
            "Shopify 商品标题": product.get("title", ""),
            "Shopify Handle": product.get("handle", ""),
            "Shopify 变体数": product.get("variants_count", 0),
        }
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="将商品映射结果导出为 CSV 格式")
    parser.add_argument(
        "--input",
        default="product_mapping.json",
        help="输入的 JSON 映射文件路径（默认: product_mapping.json）"
    )
    parser.add_argument(
        "--output",
        default="product_mapping.csv",
        help="输出的 CSV 文件路径（默认: product_mapping.csv）"
    )
    args = parser.parse_args()
    
    # 读取 JSON 文件
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ 错误: 输入文件不存在: {input_file}")
        return
    
    print(f"📖 读取映射文件: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)
    
    summary = mapping_data.get("summary", {})
    matched_pairs = mapping_data.get("matched_pairs", [])
    unmatched_printify = mapping_data.get("unmatched_printify", [])
    unmatched_shopify = mapping_data.get("unmatched_shopify", [])
    
    print(f"   ✅ 读取完成")
    print(f"   - 匹配商品对: {len(matched_pairs)}")
    print(f"   - Printify 未映射: {len(unmatched_printify)}")
    print(f"   - Shopify 未映射: {len(unmatched_shopify)}")
    print()
    
    # 创建 CSV 文件
    output_file = Path(args.output)
    print(f"📝 导出 CSV 文件: {output_file}")
    
    # CSV 列定义
    fieldnames = [
        "状态",
        "匹配类型",
        "相似度",
        "Printify ID",
        "Printify 商品标题",
        "Printify 变体数",
        "Shopify ID",
        "Shopify 商品标题",
        "Shopify Handle",
        "Shopify 变体数",
    ]
    
    with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # 写入匹配的商品对
        if matched_pairs:
            print("   ✅ 导出匹配商品对...")
            export_matched_pairs_to_csv(matched_pairs, writer)
        
        # 写入未映射的 Printify 商品
        if unmatched_printify:
            print("   ✅ 导出未映射的 Printify 商品...")
            export_unmatched_printify_to_csv(unmatched_printify, writer)
        
        # 写入未映射的 Shopify 商品
        if unmatched_shopify:
            print("   ✅ 导出未映射的 Shopify 商品...")
            export_unmatched_shopify_to_csv(unmatched_shopify, writer)
    
    print()
    print(f"✅ CSV 文件已导出: {output_file}")
    print()
    print("📊 统计信息:")
    print(f"   - 总记录数: {len(matched_pairs) + len(unmatched_printify) + len(unmatched_shopify)}")
    print(f"   - 已匹配: {len(matched_pairs)}")
    print(f"   - Printify 未映射: {len(unmatched_printify)}")
    print(f"   - Shopify 未映射: {len(unmatched_shopify)}")
    print()
    print("💡 提示:")
    print(f"   - 可以在 Excel 或 Pages 中打开: {output_file}")
    print(f"   - 使用筛选功能可以快速查看未映射的商品")


if __name__ == "__main__":
    main()
