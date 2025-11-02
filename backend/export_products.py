#!/usr/bin/env python3
"""
商品数据导出脚本
支持导出Printify和Shopify商品数据到Excel格式的表格文件
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

import requests


class ProductExporter:
    """商品数据导出器"""
    
    def __init__(self):
        self.printify_token = None
        self.shopify_token = None
        self.shopify_shop_id = None
        self.printify_shop_id = None
        
    def load_config(self, config_file: str = "product_export_config.json") -> bool:
        """从配置文件加载API配置"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.printify_token = config.get('printify_token')
                self.shopify_token = config.get('shopify_token')
                self.shopify_shop_id = config.get('shopify_shop_id')
                self.printify_shop_id = config.get('printify_shop_id')
                
                print(f"✅ 配置文件加载成功: {config_file}")
                return True
            else:
                print(f"❌ 配置文件不存在: {config_file}")
                return False
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            return False
    
    def create_config_template(self, config_file: str = "product_export_config.json"):
        """创建配置文件模板"""
        config_template = {
            "printify_token": "your_printify_token_here",
            "printify_shop_id": "your_printify_shop_id_here",
            "shopify_token": "your_shopify_token_here", 
            "shopify_shop_id": "your_shopify_shop_id_here"
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_template, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 配置文件模板已创建: {config_file}")
        print("请编辑配置文件，填入正确的API Token和Shop ID")
    
    def export_printify_products(self) -> Optional[str]:
        """导出Printify商品数据"""
        if not self.printify_token or not self.printify_shop_id:
            print("❌ Printify配置不完整，请检查配置文件")
            return None
        
        try:
            print(f"🔍 开始获取Printify商品数据 (店铺ID: {self.printify_shop_id})")
            
            headers = {
                'Authorization': f'Bearer {self.printify_token}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://api.printify.com/v1/shops/{self.printify_shop_id}/products.json"
            
            try:
                response = requests.get(url, headers=headers, timeout=30.0)
            except requests.exceptions.RequestException as e:
                print(f"❌ Printify API请求异常: {e}")
                return None
            
            # 详细的错误处理
            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Printify API请求失败:")
                print(f"   状态码: {response.status_code}")
                print(f"   URL: {url}")
                print(f"   错误信息: {error_text[:500]}")
                return None
            
            try:
                data = response.json()
            except Exception as e:
                print(f"❌ Printify API响应解析失败: {e}")
                print(f"   响应内容: {response.text[:500]}")
                return None
            
            products = data.get('data', [])
            
            if not products:
                print(f"⚠️ 警告: Printify API返回了空商品列表")
            
            print(f"✅ 成功获取Printify商品数据: {len(products)}个商品")
            
            # 生成表格数据
            output_lines = []
            output_lines.append("=== Printify 商品数据表格（店铺" + self.printify_shop_id + "）- 完整版 ===")
            output_lines.append(f"总计商品数量: {len(products)}")
            output_lines.append("")
            output_lines.append("请复制以下表格数据到Excel:")
            output_lines.append("")
            
            # 表头
            headers = [
                '商品ID', '商品标题', '商品描述', '标签', '是否可见', '发布状态',
                '蓝图ID', '打印提供商ID', '用户ID', '店铺ID', '销售渠道',
                '创建时间', '更新时间', '图片数量', '变体数量', '变体详情',
                '选项配置', '运输状态', '库存状态', '库存数量'
            ]
            output_lines.append('\t'.join(headers))
            
            # 商品数据
            for product in products:
                row = []
                row.append(str(product.get('id', '')))
                row.append(product.get('title', ''))
                
                # 处理描述
                description = product.get('description', '')
                description = description.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                if len(description) > 100:
                    description = description[:100] + "..."
                row.append(description)
                
                # 处理标签
                tags = product.get('tags', [])
                row.append(', '.join(tags) if tags else '')
                
                row.append(str(product.get('visible', '')))
                
                # 发布状态
                status = "Published" if product.get('external', {}).get('id') else "Draft"
                row.append(status)
                
                row.append(str(product.get('blueprint_id', '')))
                row.append(str(product.get('print_provider_id', '')))
                row.append(str(product.get('user_id', '')))
                row.append(str(product.get('shop_id', '')))
                row.append(product.get('sales_channel', ''))
                row.append(product.get('created_at', ''))
                row.append(product.get('updated_at', ''))
                row.append(str(len(product.get('images', []))))
                row.append(str(len(product.get('variants', []))))
                
                # 变体详情
                variant_details = []
                for variant in product.get('variants', []):
                    variant_details.append(f"{variant.get('title', '')} (${variant.get('price', 0)/100:.2f})")
                row.append('; '.join(variant_details))
                
                # 选项配置
                option_details = []
                for option in product.get('options', []):
                    values = [v.get('title', '') for v in option.get('values', [])]
                    option_details.append(f"{option.get('name', '')}: {', '.join(values)}")
                row.append('; '.join(option_details))
                
                # 运输状态
                shipping_status = []
                if product.get('is_printify_express_eligible'):
                    shipping_status.append("Express Eligible")
                if product.get('is_economy_shipping_eligible'):
                    shipping_status.append("Economy Eligible")
                if product.get('is_economy_shipping_enabled'):
                    shipping_status.append("Economy Enabled")
                if product.get('is_printify_express_enabled'):
                    shipping_status.append("Express Enabled")
                row.append('; '.join(shipping_status))
                
                # 库存状态和数量
                inventory_status = []
                total_inventory = 0
                for variant in product.get('variants', []):
                    if variant.get('is_enabled'):
                        inventory_status.append("Enabled")
                    else:
                        inventory_status.append("Disabled")
                    total_inventory += variant.get('quantity', 0)
                row.append('; '.join(inventory_status))
                row.append(str(total_inventory))
                
                output_lines.append('\t'.join(row))
            
            output_lines.append("")
            output_lines.append("=== 使用说明 ===")
            output_lines.append("1. 复制上面的表格数据")
            output_lines.append("2. 打开Excel")
            output_lines.append("3. 粘贴数据到A1单元格")
            output_lines.append("4. Excel会自动识别制表符分隔的列")
            output_lines.append("5. 调整列宽以适应内容")
            
            # 保存到文件（保存到temp目录）
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            filename = os.path.join(temp_dir, f"printify_products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            
            print(f"✅ Printify商品数据已导出到: {filename}")
            return filename
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Printify API请求异常: {e}")
            print(f"   请检查:")
            print(f"   1. printify_shop_id 是否正确")
            print(f"   2. printify_token 是否有效")
            print(f"   3. 网络连接是否正常")
            import traceback
            print(f"   详细错误: {traceback.format_exc()[:500]}")
            return None
        except Exception as e:
            print(f"❌ Printify商品数据导出失败: {e}")
            import traceback
            print(f"   详细错误: {traceback.format_exc()[:500]}")
            return None
    
    def export_shopify_products(self) -> Optional[str]:
        """导出Shopify商品数据"""
        if not self.shopify_token or not self.shopify_shop_id:
            print("❌ Shopify配置不完整，请检查配置文件")
            return None
        
        try:
            print(f"🔍 开始获取Shopify商品数据 (店铺ID: {self.shopify_shop_id})")
            
            headers = {
                'X-Shopify-Access-Token': self.shopify_token,
                'Content-Type': 'application/json'
            }
            
            url = f"https://{self.shopify_shop_id}.myshopify.com/admin/api/2024-10/products.json"
            
            try:
                response = requests.get(url, headers=headers, timeout=30.0)
            except requests.exceptions.RequestException as e:
                print(f"❌ Shopify API请求异常: {e}")
                return None
            
            # 详细的错误处理
            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Shopify API请求失败:")
                print(f"   状态码: {response.status_code}")
                print(f"   URL: {url}")
                print(f"   错误信息: {error_text[:500]}")  # 只显示前500字符
                return None
            
            try:
                data = response.json()
            except Exception as e:
                print(f"❌ Shopify API响应解析失败: {e}")
                print(f"   响应内容: {response.text[:500]}")
                return None
            
            products = data.get('products', [])
            
            if not products:
                print(f"⚠️ 警告: Shopify API返回了空商品列表")
                print(f"   响应数据: {json.dumps(data, indent=2)[:500]}")
            
            print(f"✅ 成功获取Shopify商品数据: {len(products)}个商品")
            
            # 生成表格数据
            output_lines = []
            output_lines.append("=== Shopify 商品数据表格（店铺" + self.shopify_shop_id + "）- 完整版 ===")
            output_lines.append(f"总计商品数量: {len(products)}")
            output_lines.append("")
            output_lines.append("请复制以下表格数据到Excel:")
            output_lines.append("")
            
            # 表头
            headers = [
                '商品ID', '商品标题', '商品描述', '商品状态', '商品类型', '商品标签',
                '供应商', '创建时间', '更新时间', '变体数量', '变体详情', '价格范围',
                '库存状态', '库存数量', '图片数量', '图片信息', 'SEO标题', 'SEO描述',
                '商品URL', '商品句柄'
            ]
            output_lines.append('\t'.join(headers))
            
            # 商品数据
            for product in products:
                row = []
                row.append(str(product.get('id', '')))
                row.append(product.get('title', ''))
                
                # 处理描述
                description = product.get('body_html', '')
                # 移除HTML标签
                import re
                description = re.sub(r'<[^>]+>', '', description)
                description = description.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                if len(description) > 100:
                    description = description[:100] + "..."
                row.append(description)
                
                row.append(product.get('status', ''))
                row.append(product.get('product_type', ''))
                row.append(product.get('tags', ''))
                row.append(product.get('vendor', ''))
                row.append(product.get('created_at', ''))
                row.append(product.get('updated_at', ''))
                row.append(str(len(product.get('variants', []))))
                
                # 变体详情
                variant_details = []
                for variant in product.get('variants', []):
                    variant_details.append(f"{variant.get('title', '')} (${variant.get('price', 0)})")
                row.append('; '.join(variant_details))
                
                # 价格范围
                variants = product.get('variants', [])
                if variants:
                    prices = [float(v.get('price', 0)) for v in variants]
                    min_price = min(prices)
                    max_price = max(prices)
                    if min_price == max_price:
                        price_range = f"${min_price:.2f}"
                    else:
                        price_range = f"${min_price:.2f} - ${max_price:.2f}"
                else:
                    price_range = ""
                row.append(price_range)
                
                # 库存状态和数量
                inventory_status = []
                total_inventory = 0
                for variant in product.get('variants', []):
                    if variant.get('inventory_management') == 'shopify':
                        inventory_status.append("Managed")
                    else:
                        inventory_status.append("Not Managed")
                    total_inventory += variant.get('inventory_quantity', 0)
                row.append('; '.join(inventory_status))
                row.append(str(total_inventory))
                
                row.append(str(len(product.get('images', []))))
                
                # 图片信息
                image_urls = [img.get('src', '') for img in product.get('images', [])]
                row.append('; '.join(image_urls))
                
                row.append(product.get('seo_title', ''))
                row.append(product.get('seo_description', ''))
                row.append(product.get('product_url', ''))
                row.append(product.get('handle', ''))
                
                output_lines.append('\t'.join(row))
            
            output_lines.append("")
            output_lines.append("=== 使用说明 ===")
            output_lines.append("1. 复制上面的表格数据")
            output_lines.append("2. 打开Excel")
            output_lines.append("3. 粘贴数据到A1单元格")
            output_lines.append("4. Excel会自动识别制表符分隔的列")
            output_lines.append("5. 调整列宽以适应内容")
            
            # 保存到文件（保存到temp目录）
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            filename = os.path.join(temp_dir, f"shopify_products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            
            print(f"✅ Shopify商品数据已导出到: {filename}")
            return filename
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Shopify API请求异常: {e}")
            print(f"   请检查:")
            print(f"   1. shopify_shop_id 格式是否正确（应该是店铺名，如'myshop'，不是'x0ri77-4v'）")
            print(f"   2. shopify_token 是否有效")
            print(f"   3. 网络连接是否正常")
            import traceback
            print(f"   详细错误: {traceback.format_exc()[:500]}")
            return None
        except Exception as e:
            print(f"❌ Shopify商品数据导出失败: {e}")
            import traceback
            print(f"   详细错误: {traceback.format_exc()[:500]}")
            return None
    
    def export_all_products(self) -> List[str]:
        """导出所有商品数据"""
        exported_files = []
        
        print("🚀 开始导出商品数据...")
        print("=" * 50)
        
        # 导出Printify商品
        printify_file = self.export_printify_products()
        if printify_file:
            exported_files.append(printify_file)
        
        print("=" * 50)
        
        # 导出Shopify商品
        shopify_file = self.export_shopify_products()
        if shopify_file:
            exported_files.append(shopify_file)
        
        print("=" * 50)
        print(f"✅ 导出完成！共导出 {len(exported_files)} 个文件")
        for file in exported_files:
            print(f"  - {file}")
        
        return exported_files


def main():
    """主函数"""
    exporter = ProductExporter()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--create-config":
            exporter.create_config_template()
            return
        elif sys.argv[1] == "--help":
            print("商品数据导出脚本")
            print("用法:")
            print("  python export_products.py                    # 导出所有商品数据")
            print("  python export_products.py --create-config    # 创建配置文件模板")
            print("  python export_products.py --help            # 显示帮助信息")
            return
    
    # 加载配置
    if not exporter.load_config():
        print("请先创建配置文件:")
        print("python export_products.py --create-config")
        return
    
    # 导出商品数据
    exporter.export_all_products()


if __name__ == "__main__":
    main()

