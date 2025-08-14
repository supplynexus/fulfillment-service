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
2. 使用 `quick_create_order.sh` 创建测试数据

### 生产环境
1. 使用 `full_resync.sh` 进行数据同步
2. 使用 `start_celery.sh` / `stop_celery.sh` 管理后台任务

### 故障排除
1. 使用 `check_dependencies.py` 检查环境依赖
2. 使用 `db.py` 检查数据库状态

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

### 管理工具
- `start_celery.sh` / `stop_celery.sh` - Celery管理
- `db.py` - 数据库工具

### 快速工具
- `quick_create_order.sh` - 快速创建订单
