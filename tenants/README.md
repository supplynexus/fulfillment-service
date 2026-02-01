# Tenant 配置目录

## ⚠️ 重要安全提醒

**此目录下的所有敏感文件（*.token, login_info.json, credentials.json 等）都不会被提交到 Git！**

## 目录结构

```
tenants/
├── .gitkeep
├── README.md
└── {tenant_name}/
    ├── .gitkeep
    └── {service_name}/          # 例如: printify, shopify, etc.
        ├── .gitkeep
        ├── README.md
        ├── api_token.token      # API token（敏感，不提交）
        ├── login_info.json      # 登录信息和配置（敏感，不提交）
        └── credentials.json     # 其他凭据（敏感，不提交）
```

## 当前 Tenant

### IMPEACH

- **目录**: `tenants/impeach/`
- **Printify 配置**: `tenants/impeach/printify/`
  - API Token: `api_token.token`
  - 登录信息: `login_info.json`
  - 当前使用的店铺: ID 24981565（已连接到 Shopify）

## 使用方式

### 在脚本中使用

```bash
# 使用 tenant 配置（推荐）
python scripts/get_printify_green_store_products.py --tenant impeach

# 指定店铺 ID
python scripts/get_printify_green_store_products.py --tenant impeach --shop-id 24981565
```

### 在代码中读取

```python
import json
from pathlib import Path

def get_tenant_config(tenant_name: str, service: str = "printify"):
    """获取指定 tenant 的配置"""
    tenant_dir = Path("tenants") / tenant_name / service
    
    config = {}
    
    # 读取 API token
    token_file = tenant_dir / "api_token.token"
    if token_file.exists():
        with open(token_file, "r") as f:
            config["api_token"] = f.read().strip()
    
    # 读取登录信息
    login_info_file = tenant_dir / "login_info.json"
    if login_info_file.exists():
        with open(login_info_file, "r") as f:
            config["login_info"] = json.load(f)
    
    return config
```

## 安全规范

### 文件权限

所有敏感文件应设置适当的权限：

```bash
chmod 600 tenants/**/*.token
chmod 600 tenants/**/login_info.json
chmod 600 tenants/**/credentials.json
```

### Git 忽略规则

以下文件类型已被 `.gitignore` 忽略：

- `tenants/**/*.token` - API tokens
- `tenants/**/login_info.json` - 登录信息
- `tenants/**/credentials.json` - 其他凭据
- `tenants/**/*.key` - 密钥文件
- `tenants/**/*.pem` - PEM 格式密钥

### 验证配置

定期检查确保敏感文件未被跟踪：

```bash
# 检查文件是否被忽略
git check-ignore -v tenants/impeach/printify/api_token.token
git check-ignore -v tenants/impeach/printify/login_info.json

# 检查是否有未跟踪的敏感文件
git status tenants/
```

## 添加新 Tenant

1. 创建 tenant 目录：
   ```bash
   mkdir -p tenants/{tenant_name}/{service_name}
   ```

2. 创建必要的文件：
   - `api_token.token` - API token
   - `login_info.json` - 登录信息和配置
   - `README.md` - 说明文档

3. 设置文件权限：
   ```bash
   chmod 600 tenants/{tenant_name}/{service_name}/*.token
   chmod 600 tenants/{tenant_name}/{service_name}/login_info.json
   ```

4. 验证 Git 忽略：
   ```bash
   git check-ignore -v tenants/{tenant_name}/{service_name}/*.token
   ```

## 注意事项

- ✅ **正确做法**：敏感文件只存在于本地，通过安全方式传输
- ❌ **错误做法**：将敏感文件提交到 Git 仓库
- 🔄 **定期轮换**：API tokens 到期前需要重新生成
- 🔒 **访问控制**：只有必要的用户才能访问这些文件
