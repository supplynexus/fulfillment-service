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

### 多环境支持

项目支持多个环境的数据库配置：

```
backend/
├── env.development    # 开发环境配置
├── env.staging       # 测试环境配置
└── .env              # 默认环境配置（如果存在）
```

### 使用方法

```bash
# 使用开发环境
ENV_FILE=../deployment/environments/env.development python scripts/db.py current

# 使用测试环境
ENV_FILE=../deployment/environments/env.staging python scripts/db.py upgrade

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
ENV_FILE=../deployment/environments/env.development python scripts/db.py <command>
```

## 故障排除

### 路径问题
确保在 `backend/` 目录下执行所有命令。

### 模型导入问题
检查 `migrations/env.py` 中的路径配置是否正确。

### 数据库连接问题
验证环境变量和数据库服务是否正常运行。

## 最佳实践

1. **迁移文件命名**：使用描述性的消息，如 "添加用户表索引"
2. **测试迁移**：在生产环境应用前，先在测试环境验证
3. **备份数据**：重要变更前备份数据库
4. **版本控制**：将迁移文件提交到版本控制系统
