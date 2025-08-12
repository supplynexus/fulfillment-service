# 🗄️ 数据库管理指南

## 📋 概述
本文档详细说明如何在不同的环境中管理数据库，包括迁移、备份、恢复等操作。

## 🌍 环境差异

### 环境类型对比

| 环境 | Python环境 | Docker环境 | 推荐工具 | 环境文件路径 | 实际读取文件 |
|------|------------|------------|----------|--------------|--------------|
| **Local** | ✅ 有虚拟环境 | ✅ 可选 | `./scripts/db/alembic.sh` | `backend/.env.local` | `backend/.env.local` |
| **Develop** | ❌ 无 | ✅ 必需 | `./deployment/scripts/db-docker.sh` | `deployment/environments/env.dev` | `deployment/environments/env.dev` |
| **Staging** | ❌ 无 | ✅ 必需 | `./deployment/scripts/db-docker.sh` | `deployment/environments/env.stg` | `deployment/environments/env.stg` |
| **Production** | ❌ 无 | ✅ 必需 | `./deployment/scripts/db-docker.sh` | `deployment/environments/env.prod` | `deployment/environments/env.prod` |

### 关键区别

- **Local环境**: 有Python虚拟环境，可以直接执行alembic命令
- **服务器环境**: 只有Docker环境，必须使用容器化脚本

## 🚀 数据库迁移

### Local环境操作

#### 前提条件
```bash
cd backend
source .venv/bin/activate
```

#### 常用命令
```bash
# 检查当前状态
./scripts/db/alembic.sh local current

# 查看迁移历史
./scripts/db/alembic.sh local history

# 应用所有迁移
./scripts/db/alembic.sh local upgrade

# 生成新迁移
./scripts/db/alembic.sh local autogen "add new feature"

# 降级到上一版本
./scripts/db/alembic.sh local downgrade

# 创建手动迁移
./scripts/db/alembic.sh local revision "manual migration"
```

### 服务器环境操作

#### Develop环境
```bash
# 检查当前状态
./deployment/scripts/db-docker.sh dev current

# 查看迁移历史
./deployment/scripts/db-docker.sh dev history

# 应用所有迁移
./deployment/scripts/db-docker.sh dev upgrade

# 生成新迁移
./deployment/scripts/db-docker.sh dev autogen "add new feature"

# 降级到上一版本
./deployment/scripts/db-docker.sh dev downgrade
```

#### Staging环境
```bash
# 应用所有迁移
./deployment/scripts/db-docker.sh stg upgrade

# 检查当前状态
./deployment/scripts/db-docker.sh stg current
```

#### Production环境
```bash
# 应用所有迁移（谨慎操作）
./deployment/scripts/db-docker.sh prod upgrade

# 检查当前状态
./deployment/scripts/db-docker.sh prod current
```

## 🔧 环境配置

### 环境文件读取机制

#### 1. Local环境 - `./scripts/db/alembic.sh`
```bash
# 脚本内部逻辑
case "$ENVIRONMENT" in
    local)
        ENV_FILE_PATH="$BACKEND_DIR/.env.local"
        ;;
esac

# 实际读取文件
backend/.env.local
```

#### 2. 服务器环境 - `./deployment/scripts/db-docker.sh`
```bash
# 脚本内部逻辑
case "$ENVIRONMENT" in
    local|dev|stg|prod)
        ENV_FILE="env.$ENVIRONMENT"
        ;;
esac

# 实际读取文件路径
ENV_FILE_PATH="$(dirname "$0")/../environments/$ENV_FILE"

# 具体文件位置
deployment/environments/env.dev    # Develop环境
deployment/environments/env.stg    # Staging环境  
deployment/environments/env.prod   # Production环境
```

### 环境文件配置示例

#### Local环境配置 (`backend/.env.local`)
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://supplynexus_admin:password@localhost:5433/supplynexus
DATABASE_URL_SYNC=postgresql://supplynexus_admin:password@localhost:5433/supplynexus

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 安全配置
SECRET_KEY=your-secret-key
HASHIDS_SALT=your-hashids-salt
```

#### Develop环境配置 (`deployment/environments/env.dev`)
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://supplynexus_admin:password@localhost:5433/supplynexus_dev
DATABASE_URL_SYNC=postgresql://supplynexus_admin:password@localhost:5433/supplynexus_dev

# Redis配置
REDIS_URL=redis://localhost:6379/0

# 安全配置
SECRET_KEY=dev-secret-key
HASHIDS_SALT=dev-hashids-salt
```

#### Production环境配置 (`deployment/environments/env.prod`)
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://supplynexus_admin:password@prod-db:5432/supplynexus_prod
DATABASE_URL_SYNC=postgresql://supplynexus_admin:password@prod-db:5432/supplynexus_prod

# Redis配置
REDIS_URL=redis://prod-redis:6379/0

# 安全配置
SECRET_KEY=prod-secret-key-change-this
HASHIDS_SALT=prod-hashids-salt-change-this
```

## 📊 数据库备份和恢复

### Local环境备份
```bash
# 备份数据库
pg_dump -h localhost -p 5433 -U supplynexus_admin supplynexus > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
psql -h localhost -p 5433 -U supplynexus_admin supplynexus < backup_file.sql
```

### 服务器环境备份
```bash
# 使用Docker备份
docker exec -t postgres_container pg_dumpall -c -U supplynexus_admin > backup_$(date +%Y%m%d_%H%M%S).sql

# 使用Docker恢复
cat backup_file.sql | docker exec -i postgres_container psql -U supplynexus_admin
```

## 🔍 数据库监控

### 检查数据库状态
```bash
# Local环境
psql -h localhost -p 5433 -U supplynexus_admin -d supplynexus -c "SELECT version();"

# 服务器环境
docker exec -it postgres_container psql -U supplynexus_admin -d supplynexus -c "SELECT version();"
```

### 查看表结构
```bash
# 查看所有表
\dt

# 查看特定表结构
\d table_name

# 查看索引
\di
```

## ⚠️ 注意事项

### 迁移安全
1. **生产环境**: 迁移前必须备份数据库
2. **测试环境**: 先在staging环境测试迁移
3. **回滚准备**: 确保可以快速回滚到上一版本

### 环境隔离
1. **数据隔离**: 不同环境使用不同的数据库
2. **配置隔离**: 每个环境有独立的环境文件
3. **权限隔离**: 生产环境使用最小权限原则

### 性能考虑
1. **大表迁移**: 避免在业务高峰期执行
2. **索引重建**: 大量数据变更后重建索引
3. **监控**: 迁移过程中监控数据库性能

## 🆘 故障排除

### 常见问题

#### 1. 连接失败
```bash
# 检查数据库服务状态
docker-compose ps postgres

# 检查网络连接
docker network ls
```

#### 2. 权限问题
```bash
# 检查用户权限
psql -h localhost -p 5433 -U supplynexus_admin -d supplynexus -c "\du"
```

#### 3. 迁移冲突
```bash
# 查看迁移历史
alembic history

# 检查迁移文件
cat migrations/versions/latest_migration.py
```

### 紧急恢复
```bash
# 回滚到上一版本
alembic downgrade -1

# 强制标记版本
alembic stamp <revision_id>
```

## 📚 相关文档

- [开发工作流](./DEVELOPMENT_WORKFLOW.md)
- [快速开始指南](./QUICK_START.md)
- [API文档](./api/)

## 📞 支持

如有问题，请：
1. 查看本文档的故障排除部分
2. 检查相关日志文件
3. 联系开发团队

---

**最后更新**: 2025-08-12  
**维护者**: SupplyNexus Team
