# 🚀 新服务器快速设置指南

## 一键设置（推荐）

如果您已经将项目文件复制到服务器，可以使用快速设置脚本：

```bash
# 1. 进入部署目录
cd deployment/docker

# 2. 设置脚本权限
chmod +x setup_infrastructure.sh

# 3. 运行设置脚本
./setup_infrastructure.sh

# 4. 编辑配置文件（重要！）
# 修改 PostgreSQL 密码
nano ~/supplynexus/infrastructure/postgresql/.env

# 修改 Redis 密码
nano ~/supplynexus/infrastructure/redis/.env

# 5. 启动服务
cd ~/supplynexus/infrastructure/postgresql && ./deploy.sh prod up
cd ~/supplynexus/infrastructure/redis && ./deploy.sh prod up
```

## 手动设置步骤

### 1. 准备配置文件

在服务器上创建目录并复制配置文件：

```bash
# 创建目录
mkdir -p ~/supplynexus/infrastructure/{postgresql,redis}

# 复制 PostgreSQL 配置文件
cp deployment/docker/postgresql/* ~/supplynexus/infrastructure/postgresql/

# 复制 Redis 配置文件
cp deployment/docker/redis/* ~/supplynexus/infrastructure/redis/
```

### 2. 配置 PostgreSQL

```bash
cd ~/supplynexus/infrastructure/postgresql

# 创建环境配置
cp environment.example .env

# 编辑配置（必须修改密码！）
nano .env
```

**必须修改的配置：**
- `POSTGRES_PASSWORD`: 设置强密码
- `CONTAINER_NAME`: 根据环境修改（如：supplynexus-postgres-prod）
- `POSTGRES_PORT`: 根据环境选择端口（生产环境建议 5435）
- `DATA_DIR`: 数据存储目录

### 3. 配置 Redis

```bash
cd ~/supplynexus/infrastructure/redis

# 创建环境配置
cp environment.example .env

# 编辑配置（必须修改密码！）
nano .env
```

**必须修改的配置：**
- `REDIS_PASSWORD`: 设置强密码
- `CONTAINER_NAME`: 根据环境修改（如：supplynexus-redis-prod）
- `REDIS_PORT`: 根据环境选择端口（生产环境建议 6382）
- `DATA_DIR`: 数据存储目录

### 4. 启动服务

```bash
# 启动 PostgreSQL
cd ~/supplynexus/infrastructure/postgresql
chmod +x deploy.sh
./deploy.sh prod up

# 启动 Redis
cd ~/supplynexus/infrastructure/redis
chmod +x deploy.sh
./deploy.sh prod up
```

### 5. 验证服务

```bash
# 检查容器状态
docker ps | grep -E 'postgres|redis'

# 测试 PostgreSQL
cd ~/supplynexus/infrastructure/postgresql
docker-compose exec postgresql psql -U supplynexus_admin -d supplynexus -c "SELECT version();"

# 测试 Redis
cd ~/supplynexus/infrastructure/redis
docker-compose exec redis redis-cli -a YOUR_PASSWORD PING
```

## 📋 环境配置示例

### PostgreSQL (.env)

```bash
POSTGRES_DB=supplynexus
POSTGRES_USER=supplynexus_admin
POSTGRES_PASSWORD=your-strong-password-here
CONTAINER_NAME=supplynexus-postgres-prod
POSTGRES_PORT=5435
DATA_DIR=./data-prod
```

### Redis (.env)

```bash
REDIS_PASSWORD=your-strong-password-here
CONTAINER_NAME=supplynexus-redis-prod
REDIS_PORT=6382
DATA_DIR=./data-prod
```

## 🔗 连接信息

### PostgreSQL 连接字符串

```
postgresql://supplynexus_admin:your-password@your-server-ip:5435/supplynexus
```

### Redis 连接字符串

```
redis://:your-password@your-server-ip:6382/0
```

## 🛠️ 常用命令

```bash
# PostgreSQL 管理
cd ~/supplynexus/infrastructure/postgresql
./deploy.sh prod up      # 启动
./deploy.sh prod down    # 停止
./deploy.sh prod restart # 重启
./deploy.sh prod logs    # 查看日志
./deploy.sh prod status  # 查看状态

# Redis 管理
cd ~/supplynexus/infrastructure/redis
./deploy.sh prod up      # 启动
./deploy.sh prod down    # 停止
./deploy.sh prod restart # 重启
./deploy.sh prod logs    # 查看日志
./deploy.sh prod status  # 查看状态
```

## ⚠️ 重要提示

1. **必须修改默认密码** - 安全第一！
2. **配置防火墙** - 限制数据库端口访问
3. **定期备份** - 数据目录需要定期备份
4. **监控磁盘空间** - 确保有足够空间存储数据

## 📚 详细文档

- 完整部署指南: [SETUP_NEW_SERVER.md](./SETUP_NEW_SERVER.md)
- PostgreSQL 配置: [postgresql/README.md](./postgresql/README.md)
