# Tenant: IMPEACH - Printify 配置

## ⚠️ 安全提醒

**此目录包含敏感的登录信息和 API tokens，绝对不要提交到 Git！**

## 文件说明

- `api_token.token` - Printify Personal Access Token
- `login_info.json` - Printify 登录信息和店铺配置
- `README.md` - 本说明文档

## 登录信息

- **邮箱**: leo.zhang7605@gmail.com
- **密码**: Impeach@2025
- **Dashboard**: https://printify.com/app/dashboard

## API Token

- **Token 名称**: prod_20260201
- **创建日期**: 2025-02-01
- **有效期**: 1年（到 2026-02-01）
- **文件**: `api_token.token`

## 当前使用的店铺（绿色店铺）

- **店铺 ID**: 24981565
- **店铺名称**: IMPEACH
- **连接状态**: ✅ 已连接到 Shopify
- **销售渠道**: shopify
- **商品总数**: 70 个

## 所有店铺

### 店铺 1 (未连接)
- **店铺 ID**: 21704929
- **店铺名称**: IMPEACH
- **连接状态**: ❌ 未连接
- **销售渠道**: disconnected

### 店铺 2 (已连接 - 当前使用)
- **店铺 ID**: 24981565
- **店铺名称**: IMPEACH
- **连接状态**: ✅ 已连接
- **销售渠道**: shopify

## 使用方法

### 在脚本中使用

```bash
# 使用 tenant 目录下的 token
python scripts/get_printify_green_store_products.py \
  --token-file tenants/impeach/printify/api_token.token \
  --shop-id 24981565
```

### 在代码中读取

```python
import json
from pathlib import Path

def get_impeach_printify_config():
    """获取 IMPEACH tenant 的 Printify 配置"""
    tenant_dir = Path(__file__).parent.parent / "tenants" / "impeach" / "printify"
    
    # 读取登录信息
    with open(tenant_dir / "login_info.json", "r") as f:
        login_info = json.load(f)
    
    # 读取 API token
    with open(tenant_dir / "api_token.token", "r") as f:
        api_token = f.read().strip()
    
    return {
        "api_token": api_token,
        "login_info": login_info,
        "active_shop_id": login_info["active_shop"]["shop_id"]
    }
```

## 安全最佳实践

1. **文件权限**: 设置适当的文件权限
   ```bash
   chmod 600 tenants/impeach/printify/api_token.token
   chmod 600 tenants/impeach/printify/login_info.json
   ```

2. **不要提交**: 确保 `.gitignore` 包含此目录
   ```gitignore
   tenants/**/*.token
   tenants/**/login_info.json
   ```

3. **定期轮换**: Token 有效期为 1 年，到期前需要重新生成

4. **访问控制**: 只有必要的用户才能访问这些文件
