# 环境配置说明

## 🌍 环境分类

### 1. Local 环境 (本地开发)
- **端口**: PostgreSQL 5432, Redis 6379
- **用途**: 本地开发调试
- **配置文件**: `deployment/environments/env.local`
- **特点**: 
  - 使用标准端口，避免冲突
  - 适合本地开发环境
  - 数据持久化在本地

### 2. Development 环境 (开发服务器)
- **端口**: PostgreSQL 5433, Redis 6380
- **用途**: 开发服务器部署
- **配置文件**: `deployment/environments/env.development`
- **特点**:
  - 使用非标准端口，避免与本地服务冲突
  - 适合团队开发环境
  - 数据持久化在服务器

### 3. Staging 环境 (测试环境)
- **端口**: PostgreSQL 5434, Redis 6381
- **用途**: 测试和预发布
- **配置文件**: `deployment/environments/env.staging`
- **特点**:
  - 模拟生产环境
  - 用于功能测试和集成测试
  - 数据可以定期重置

### 4. Production 环境 (生产环境)
- **端口**: PostgreSQL 5435, Redis 6382
- **用途**: 生产部署
- **配置文件**: `deployment/environments/env.production`
- **特点**:
  - 生产环境配置
  - 高可用性和安全性
  - 数据备份和监控

## 🔧 端口分配表

| 环境 | PostgreSQL | Redis | 说明 |
|------|------------|-------|------|
| Local | 5432 | 6379 | 本地开发 |
| Development | 5433 | 6380 | 开发服务器 |
| Staging | 5434 | 6381 | 测试环境 |
| Production | 5435 | 6382 | 生产环境 |

## 📁 配置文件位置

```
deployment/environments/
├── env.example          # 配置模板
├── env.local            # 本地环境配置
├── env.development      # 开发环境配置
├── env.staging          # 测试环境配置
└── env.production       # 生产环境配置
```

## 🚀 使用方式

### 本地开发
```bash
# 配置本地环境
cp deployment/environments/env.example deployment/environments/env.local
vim deployment/environments/env.local

# 启动本地服务
./deployment/scripts/deploy.sh local start

# 运行迁移
./deployment/scripts/deploy.sh local db-upgrade
```

### 开发服务器
```bash
# 配置开发环境
cp deployment/environments/env.example deployment/environments/env.development
vim deployment/environments/env.development

# 启动开发服务
./deployment/scripts/deploy.sh development start

# 运行迁移
./deployment/scripts/deploy.sh development db-upgrade
```

## ⚠️ 注意事项

1. **端口冲突**: 确保不同环境使用不同端口
2. **数据隔离**: 每个环境使用独立的数据库
3. **配置安全**: 生产环境配置不要提交到 git
4. **环境变量**: 使用 `ENV_FILE` 环境变量指定配置文件

## 🔄 迁移现有配置

如果你有现有的 `environment.local` 文件，可以这样迁移：

```bash
# 1. 复制现有配置到新的 local 环境
cp environment.local deployment/environments/env.local

# 2. 修改端口为本地标准端口 (5432)
vim deployment/environments/env.local
# 将端口从 5433 改为 5432

# 3. 使用新的部署脚本
./deployment/scripts/deploy.sh local start
```

## 📝 配置示例

### Local 环境配置示例
```bash
# 本地环境配置
ENVIRONMENT=local
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/database
DATABASE_URL_SYNC=postgresql://username:password@localhost:5432/database
REDIS_URL=redis://localhost:6379/0
```

### Development 环境配置示例
```bash
# 开发环境配置
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5433/database
DATABASE_URL_SYNC=postgresql://username:password@localhost:5433/database
REDIS_URL=redis://localhost:6380/0
```
