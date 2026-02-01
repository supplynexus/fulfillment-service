# Tenant: IMPEACH - Shopify 配置

## ⚠️ 安全提醒

**此目录包含敏感的登录信息和 API tokens，绝对不要提交到 Git！**

## 文件说明

- `login_info.json` - Shopify 登录信息和店铺配置
- `README.md` - 本说明文档

## 店铺信息

- **店铺 ID**: x0ri77-4v
- **店铺名称**: IMPEACH
- **店铺域名**: x0ri77-4v.myshopify.com
- **店铺 URL**: https://x0ri77-4v.myshopify.com
- **邮箱**: impeach@impeach.world
- **计划**: Shopify
- **货币**: USD

## API 配置

- **Access Token**: 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
- **API 版本**: 2024-10
- **创建日期**: 2025-02-01

## 商品统计

- **商品总数**: 42 个
- **已发布**: 42 个
- **草稿**: 0 个
- **已归档**: 0 个

## 使用方法

### 在脚本中使用

```bash
# 使用 tenant 配置（推荐）
python scripts/get_shopify_store_products.py --tenant impeach

# 仅获取店铺信息
python scripts/get_shopify_store_products.py --tenant impeach --list-shop-only

# 从配置文件读取
python scripts/get_shopify_store_products.py --config-file tenants/impeach/shopify/login_info.json
```

### 在代码中读取

```python
import json
from pathlib import Path

def get_impeach_shopify_config():
    """获取 IMPEACH tenant 的 Shopify 配置"""
    tenant_dir = Path(__file__).parent.parent / "tenants" / "impeach" / "shopify"
    
    # 读取登录信息
    with open(tenant_dir / "login_info.json", "r") as f:
        login_info = json.load(f)
    
    return {
        "shop_id": login_info["shop_id"],
        "store_url": login_info["store_url"],
        "access_token": login_info["access_token"],
        "api_version": login_info.get("api_version", "2024-10")
    }
```

## 安全最佳实践

1. **文件权限**: 设置适当的文件权限
   ```bash
   chmod 600 tenants/impeach/shopify/login_info.json
   ```

2. **不要提交**: 确保 `.gitignore` 包含此目录
   ```gitignore
   tenants/**/login_info.json
   tenants/**/*.token
   ```

3. **定期轮换**: Access Token 到期前需要重新生成

4. **访问控制**: 只有必要的用户才能访问这些文件

## API 调用示例

### 使用 GraphQL API 获取商品

```python
import httpx
import asyncio

async def get_products():
    shop_id = "x0ri77-4v"
    access_token = "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"
    api_version = "2024-10"
    
    url = f"https://{shop_id}.myshopify.com/admin/api/{api_version}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }
    
    query = """
    query {
        products(first: 10) {
            nodes {
                id
                title
                handle
                status
            }
        }
    }
    """
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json={"query": query})
        data = response.json()
        return data

# 运行
products = asyncio.run(get_products())
```
