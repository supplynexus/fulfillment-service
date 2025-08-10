# 数据库管理指南

## 架构说明

本项目采用 **服务内数据库迁移** 的架构：

```
backend/
├── alembic.ini          # Alembic 配置文件
├── migrations/          # 数据库迁移文件
│   ├── env.py          # 迁移环境配置
│   ├── script.py.mako  # 迁移文件模板
│   └── versions/       # 迁移版本文件
├── scripts/
│   └── db.py           # 数据库管理脚本
└── app/
    └── models/         # 数据模型定义
```

## 优势

✅ **开发体验好**：所有命令都在 `backend/` 目录执行  
✅ **职责清晰**：数据库迁移属于后端服务  
✅ **符合微服务架构**：每个服务管理自己的数据库变更  
✅ **部署简单**：CI/CD 流程更清晰  

## 快速开始

### 1. 激活虚拟环境
```bash
cd backend
source .venv/bin/activate
```

### 2. 使用便捷脚本（推荐）

```bash
# 查看当前迁移版本
python scripts/db.py current

# 查看迁移历史
python scripts/db.py history

# 升级到最新版本
python scripts/db.py upgrade

# 自动生成迁移文件
python scripts/db.py autogen "添加用户表"

# 创建空迁移文件
python scripts/db.py revision "手动迁移"

# 回退一个版本
python scripts/db.py downgrade

# 重置数据库（危险操作）
python scripts/db.py reset
```

### 3. 直接使用 Alembic 命令

```bash
# 查看当前版本
alembic current

# 升级数据库
alembic upgrade head

# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 查看历史
alembic history
```

## 开发流程

### 修改模型后更新数据库

1. **修改模型文件** (`app/models/`)
2. **生成迁移文件**：
   ```bash
   python scripts/db.py autogen "描述变更"
   ```
3. **检查生成的迁移文件** (`migrations/versions/`)
4. **应用迁移**：
   ```bash
   python scripts/db.py upgrade
   ```

### 手动创建迁移

```bash
python scripts/db.py revision "手动迁移描述"
```

然后编辑生成的迁移文件，添加自定义 SQL。

## 环境配置

### 重要安全配置

**健康检查 API Key 配置**：
- `HEALTH_CHECK_API_KEY` 必须配置，没有缺省值
- 用于保护健康检查端点，防止滥用
- 建议使用强随机密钥：`openssl rand -hex 32`
- 详细配置说明请参考：[健康检查安全配置指南](./docs/HEALTH_CHECK_SECURITY.md)

### 多环境支持

项目支持多个环境的数据库配置：

```
backend/
├── env.dev    # 开发环境配置
├── env.stg       # 测试环境配置
└── .env              # 默认环境配置（如果存在）
```

### 使用方法

```bash
# 使用开发环境
ENV_FILE=../deployment/environments/env.dev python scripts/db.py current

# 使用测试环境
ENV_FILE=../deployment/environments/env.stg python scripts/db.py upgrade

# 使用默认环境（不指定 ENV_FILE）
python scripts/db.py current
```

### 环境变量优先级

数据库连接通过以下优先级配置：

1. **环境变量** `DATABASE_URL_SYNC` (最高优先级)
2. **环境变量** `DATABASE_URL`
3. **环境文件中的配置**
4. **配置文件默认值** `settings.DATABASE_URL`

### 设置环境变量

```bash
# 临时设置
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5433/db"
export DATABASE_URL_SYNC="postgresql://user:pass@localhost:5433/db"

# 或使用环境文件
ENV_FILE=../deployment/environments/env.dev python scripts/db.py <command>
```

## 故障排除

### 路径问题
确保在 `backend/` 目录下执行所有命令。

### 模型导入问题
检查 `migrations/env.py` 中的路径配置是否正确。

### 数据库连接问题
验证环境变量和数据库服务是否正常运行。

## 应用启动

### 使用启动脚本（推荐）

```bash
# 进入 backend 目录
cd backend

# 生产模式启动
./scripts/start.sh

# 开发模式启动（自动重载）
./scripts/dev.sh
```

### 手动启动命令

```bash
# 进入 backend 目录
cd backend

# 激活虚拟环境并启动应用
source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 开发模式启动（自动重载）

```bash
cd backend
source .venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 后台启动

```bash
cd backend
source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

### 自定义端口启动

```bash
# 使用环境变量自定义端口
PORT=8080 ./scripts/start.sh

# 或手动指定
cd backend
source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### 访问应用

- **API 文档**：http://localhost:8000/api/v1/docs
- **健康检查**：http://localhost:8000/api/v1/health
- **API 端点**：http://localhost:8000/api/v1/

## 最佳实践

1. **迁移文件命名**：使用描述性的消息，如 "添加用户表索引"
2. **测试迁移**：在生产环境应用前，先在测试环境验证
3. **备份数据**：重要变更前备份数据库
4. **版本控制**：将迁移文件提交到版本控制系统
5. **环境配置**：确保 `.env` 文件中的 `HEALTH_CHECK_API_KEY` 已正确配置
