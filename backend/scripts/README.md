# Scripts 目录说明

本目录包含各种实用脚本，用于开发、测试和运维。

## 核心工具

### 数据同步工具

#### `full_resync.sh` / `full_resync.py`
**用途**: 完全重新同步Shopify订单和商品数据
**用法**:
```bash
# 使用Shell脚本（推荐）
./full_resync.sh

# 使用Python脚本
python3 full_resync.py

# 只同步订单
./full_resync.sh --orders-only

# 只同步商品
./full_resync.sh --products-only

# 限制数量
./full_resync.sh --max-orders 1000 --max-products 500

# 指定租户
./full_resync.sh --tenant-id 1
```

#### `check_dependencies.py`
**用途**: 检查Python 3.12环境下的所有依赖是否正确安装
**用法**:
```bash
python3.12 check_dependencies.py
```
**检查内容**:
- Python版本检查
- 核心依赖检查（FastAPI、SQLAlchemy、Celery等）
- 开发依赖检查（pytest、black、mypy等）
- 可选依赖检查（Sphinx、Flower等）
- 应用模块检查

### 代码质量检查工具

#### `quick_check.sh` / `quick_check.py`
**用途**: 快速检查代码语法和基本导入
**用法**:
```bash
# 使用Shell脚本（推荐）
./quick_check.sh

# 使用Python脚本
python3 quick_check.py
```
**检查内容**:
- Python语法检查
- 基本模块导入检查
- 快速启动前验证

#### `check_imports.sh` / `check_imports.py`
**用途**: 详细检查代码中的导入问题
**用法**:
```bash
# 检查默认目录 (app/)
./check_imports.sh

# 检查指定目录
./check_imports.sh app/api

# 使用Python脚本
python3 check_imports.py [directory]
```
**检查内容**:
- 导入语句语法检查
- 类型注解中的类型检查
- 未导入类型的使用检查

#### `check_syntax.sh` / `check_syntax.py`
**用途**: 检查Python代码语法
**用法**:
```bash
# 检查默认目录 (app/)
./check_syntax.sh

# 检查指定目录
./check_syntax.sh app/models

# 使用Python脚本
python3 check_syntax.py [directory]
```
**检查内容**:
- Python语法验证
- 文件编码检查
- 语法错误定位

#### `check_code_quality.sh` / `check_code_quality.py`
**用途**: 全面的代码质量检查
**用法**:
```bash
# 检查默认目录 (app/)
./check_code_quality.sh

# 检查指定目录
./check_code_quality.sh app/core

# 使用Python脚本
python3 check_code_quality.py [directory]
```
**检查内容**:
- 语法检查
- 导入检查
- 代码风格检查
- 文档字符串检查
- 变量命名检查

### 密钥管理工具

#### `update_tenant_public_key.sh` / `update_tenant_public_key.py`
**用途**: 从现有私钥文件更新租户的公钥到数据库
**用法**:
```bash
# 使用Shell脚本（推荐）
./update_tenant_public_key.sh <tenant_name> <private_key_file>

# 示例
./update_tenant_public_key.sh impeach ../frontend/keys/impeach_private_key.pem

# 使用Python脚本
python3 update_tenant_public_key.py <tenant_name> <private_key_file>
```
**功能**:
- 读取私钥文件
- 生成对应的公钥
- 更新数据库中的租户公钥

#### `generate_keys.sh` / `generate_keys.py`
**用途**: 生成新的RSA密钥对
**用法**:
```bash
# 生成新密钥对
./generate_keys.sh <tenant_name>

# 生成并保存到数据库
./generate_keys.sh <tenant_name> --save-db

# 使用Python脚本
python3 generate_keys.py <tenant_name> [--save-db]
```

### Celery 管理工具

#### `start_celery.sh`
**用途**: 启动Celery工作进程和定时任务
**用法**:
```bash
# 使用默认环境配置（deployment/environments/env.local）
./start_celery.sh

# 指定环境配置文件
export ENV_FILE=../deployment/environments/env.dev
./start_celery.sh

# 或者直接指定
ENV_FILE=../deployment/environments/env.dev ./start_celery.sh
```

**环境配置**:
- 默认使用 `deployment/environments/env.local`
- 可通过 `ENV_FILE` 环境变量指定其他配置文件
- 支持 local, dev, stg, prod 环境

#### `stop_celery.sh`
**用途**: 停止Celery工作进程
**用法**:
```bash
./stop_celery.sh
```

### 数据库工具

#### `db.py`
**用途**: 数据库管理脚本，支持本地和服务器环境的数据库操作
**用法**:
```bash
# 本地环境（默认使用 deployment/environments/env.local）
python scripts/db.py current
python scripts/db.py upgrade
python scripts/db.py autogen "add new feature"

# 指定环境配置文件
ENV_FILE=../deployment/environments/env.dev python scripts/db.py upgrade
ENV_FILE=../deployment/environments/env.stg python scripts/db.py upgrade
ENV_FILE=../deployment/environments/env.prod python scripts/db.py upgrade
```

**环境配置**:
- 默认使用 `deployment/environments/env.local`
- 可通过 `ENV_FILE` 环境变量指定其他配置文件
- 支持 local, dev, stg, prod 环境

### 快速工具

#### `quick_create_order.sh`
**用途**: 快速创建订单的Shell脚本
**用法**:
```bash
./quick_create_order.sh
```

## 使用建议

### 开发环境
1. 使用 `check_dependencies.py` 检查环境依赖
2. 使用 `quick_check.sh` 进行快速代码检查
3. 使用 `check_imports.sh` 检查导入问题
4. 使用 `quick_create_order.sh` 创建测试数据

### 代码质量检查
1. 开发前：使用 `quick_check.sh` 快速验证
2. 开发中：使用 `check_imports.sh` 检查导入
3. 提交前：使用 `check_code_quality.sh` 全面检查

### 密钥管理
1. 新租户：使用 `generate_keys.sh` 生成密钥对
2. 更新公钥：使用 `update_tenant_public_key.sh` 更新数据库公钥

### 生产环境
1. 使用 `full_resync.sh` 进行数据同步
2. 使用 `start_celery.sh` / `stop_celery.sh` 管理后台任务

### 故障排除
1. 使用 `check_dependencies.py` 检查环境依赖
2. 使用 `db.py` 检查数据库状态
3. 使用 `check_imports.sh` 检查代码问题

## 注意事项

1. **权限**: 确保脚本有执行权限 (`chmod +x script.sh`)
2. **环境**: 确保在正确的Python环境中运行
3. **配置**: 确保环境变量和配置文件正确设置
4. **依赖**: 确保所有必要的依赖包已安装
5. **备份**: 在生产环境中使用前，建议先备份数据

## 脚本分类

### 核心工具
- `full_resync.sh` / `full_resync.py` - 数据同步
- `check_dependencies.py` - 依赖检查工具

### 代码质量工具
- `quick_check.sh` / `quick_check.py` - 快速代码检查
- `check_imports.sh` / `check_imports.py` - 导入检查
- `check_syntax.sh` / `check_syntax.py` - 语法检查
- `check_code_quality.sh` / `check_code_quality.py` - 全面质量检查

### 密钥管理工具
- `update_tenant_public_key.sh` / `update_tenant_public_key.py` - 公钥更新
- `generate_keys.sh` / `generate_keys.py` - 密钥生成

### 管理工具
- `start_celery.sh` / `stop_celery.sh` - Celery管理
- `db.py` - 数据库工具

### 快速工具
- `quick_create_order.sh` - 快速创建订单
