# 新服务器 Redis 和 PostgreSQL 部署指南

本指南将帮助您在新服务器上快速建立 Redis 和 PostgreSQL 的 Docker 容器。

## 📋 前置要求

1. **Docker 和 Docker Compose 已安装**
   ```bash
   # 检查 Docker 版本
   docker --version
   docker-compose --version
   
   # 如果未安装，请先安装 Docker 和 Docker Compose
   ```

2. **服务器权限**
   - 确保您有 sudo 权限或 root 权限
   - 确保可以创建目录和文件

## 🚀 快速开始

### 步骤 1: 准备部署目录

在服务器上创建部署目录结构：

```bash
# 创建主目录
mkdir -p ~/supplynexus/infrastructure
cd ~/supplynexus/infrastructure

# 创建 PostgreSQL 和 Redis 目录
mkdir -p postgresql redis
```

### 步骤 2: 复制配置文件

将项目中的配置文件复制到服务器：

#### PostgreSQL 配置

```bash
# 复制 PostgreSQL 配置文件
cd ~/supplynexus/infrastructure/postgresql

# 从项目复制以下文件：
# - deployment/docker/postgresql/docker-compose.yml
# - deployment/docker/postgresql/deploy.sh
# - deployment/docker/postgresql/environment.example
```

#### Redis 配置

```bash
# 复制 Redis 配置文件
cd ~/supplynexus/infrastructure/redis

# 从项目复制以下文件：
# - deployment/docker/redis/docker-compose.yml
# - deployment/docker/redis/deploy.sh
# - deployment/docker/redis/environment.example
```

### 步骤 3: 配置环境变量

#### PostgreSQL 环境配置

```bash
cd ~/supplynexus/infrastructure/postgresql

# 复制环境配置模板
cp environment.example .env

# 编辑配置文件（重要：修改密码！）
vi .env
# 或使用 nano: nano .env
```

**必须修改的配置项：**

```bash
# PostgreSQL 配置
POSTGRES_DB=supplynexus
POSTGRES_USER=supplynexus_admin
POSTGRES_PASSWORD=your-secure-password-here-change-this  # ⚠️ 必须修改！

# 容器配置
CONTAINER_NAME=supplynexus-postgres-prod  # 根据环境修改

# 端口配置（根据环境选择）
# 本地: 5432
# 开发: 5433
# 测试: 5434
# 生产: 5435
POSTGRES_PORT=5435  # 生产环境建议使用 5435

# 数据目录配置
DATA_DIR=./data-prod  # 根据环境修改
```

#### Redis 环境配置

```bash
cd ~/supplynexus/infrastructure/redis

# 复制环境配置模板
cp environment.example .env

# 编辑配置文件（重要：修改密码！）
vi .env
# 或使用 nano: nano .env
```

**必须修改的配置项：**

```bash
# Redis 密码（重要：修改默认密码）
REDIS_PASSWORD=your-secure-redis-password-here-change-this  # ⚠️ 必须修改！

# 容器配置
CONTAINER_NAME=supplynexus-redis-prod  # 根据环境修改

# 端口配置（根据环境选择）
# 本地: 6379
# 开发: 6380
# 测试: 6381
# 生产: 6382
REDIS_PORT=6382  # 生产环境建议使用 6382

# 数据目录配置
DATA_DIR=./data-prod  # 根据环境修改
```

### 步骤 4: 设置脚本权限

```bash
# 设置 PostgreSQL 部署脚本权限
chmod +x ~/supplynexus/infrastructure/postgresql/deploy.sh

# 设置 Redis 部署脚本权限
chmod +x ~/supplynexus/infrastructure/redis/deploy.sh
```

### 步骤 5: 启动服务

#### 方式一：使用部署脚本（推荐）

**PostgreSQL:**

```bash
cd ~/supplynexus/infrastructure/postgresql

# 启动服务（使用 .env 文件）
./deploy.sh prod up

# 或者手动指定环境
docker-compose --env-file .env up -d
```

**Redis:**

```bash
cd ~/supplynexus/infrastructure/redis

# 启动服务（使用 .env 文件）
./deploy.sh prod up

# 或者手动指定环境
docker-compose --env-file .env up -d
```

#### 方式二：直接使用 Docker Compose

**PostgreSQL:**

```bash
cd ~/supplynexus/infrastructure/postgresql
docker-compose up -d
```

**Redis:**

```bash
cd ~/supplynexus/infrastructure/redis
docker-compose up -d
```

### 步骤 6: 验证服务

#### 检查容器状态

```bash
# 检查 PostgreSQL 容器
docker ps | grep postgres

# 检查 Redis 容器
docker ps | grep redis

# 或者查看所有容器
docker ps
```

#### 测试 PostgreSQL 连接

```bash
# 进入 PostgreSQL 容器测试
cd ~/supplynexus/infrastructure/postgresql
docker-compose exec postgresql psql -U supplynexus_admin -d supplynexus

# 在 PostgreSQL 中执行测试命令
# \l  # 列出所有数据库
# \q  # 退出
```

#### 测试 Redis 连接

```bash
# 进入 Redis 容器测试
cd ~/supplynexus/infrastructure/redis
docker-compose exec redis redis-cli -a your-secure-redis-password-here-change-this

# 在 Redis 中执行测试命令
# PING  # 应该返回 PONG
# INFO  # 查看 Redis 信息
# exit  # 退出
```

## 📝 常用操作命令

### PostgreSQL 管理

```bash
cd ~/supplynexus/infrastructure/postgresql

# 启动服务
./deploy.sh prod up
# 或: docker-compose up -d

# 停止服务
./deploy.sh prod down
# 或: docker-compose down

# 重启服务
./deploy.sh prod restart
# 或: docker-compose restart

# 查看日志
./deploy.sh prod logs
# 或: docker-compose logs -f

# 查看状态
./deploy.sh prod status
# 或: docker-compose ps
```

### Redis 管理

```bash
cd ~/supplynexus/infrastructure/redis

# 启动服务
./deploy.sh prod up
# 或: docker-compose up -d

# 停止服务
./deploy.sh prod down
# 或: docker-compose down

# 重启服务
./deploy.sh prod restart
# 或: docker-compose restart

# 查看日志
./deploy.sh prod logs
# 或: docker-compose logs -f

# 查看状态
./deploy.sh prod status
# 或: docker-compose ps
```

## 🔧 连接信息

### PostgreSQL 连接字符串

```
postgresql://supplynexus_admin:your-password@your-server-ip:5435/supplynexus
```

**连接参数：**
- **Host**: 服务器 IP 地址
- **Port**: 5435 (生产环境) 或根据 .env 配置
- **Database**: supplynexus
- **Username**: supplynexus_admin
- **Password**: 您在 .env 中设置的密码

### Redis 连接字符串

```
redis://:your-password@your-server-ip:6382/0
```

**连接参数：**
- **Host**: 服务器 IP 地址
- **Port**: 6382 (生产环境) 或根据 .env 配置
- **Password**: 您在 .env 中设置的密码
- **Database**: 0 (默认)

## 🛡️ 安全建议

1. **修改默认密码**
   - PostgreSQL: 修改 `POSTGRES_PASSWORD`
   - Redis: 修改 `REDIS_PASSWORD`
   - 使用强密码（至少 16 个字符，包含大小写字母、数字和特殊字符）

2. **防火墙配置**
   ```bash
   # 只允许特定 IP 访问 PostgreSQL
   sudo ufw allow from YOUR_APP_SERVER_IP to any port 5435
   
   # 只允许特定 IP 访问 Redis
   sudo ufw allow from YOUR_APP_SERVER_IP to any port 6382
   
   # 或者完全禁止外部访问（如果应用在同一服务器）
   # 不开放端口，只允许本地连接
   ```

3. **定期备份**
   ```bash
   # PostgreSQL 备份
   docker-compose exec postgresql pg_dump -U supplynexus_admin supplynexus > backup_$(date +%Y%m%d).sql
   
   # Redis 备份（数据已持久化到 ./data-prod 目录）
   tar -czf redis_backup_$(date +%Y%m%d).tar.gz ./data-prod
   ```

4. **监控和日志**
   - 定期检查容器日志
   - 监控磁盘空间使用
   - 设置日志轮转

## 📁 数据持久化

数据存储在以下目录：

- **PostgreSQL**: `~/supplynexus/infrastructure/postgresql/data-prod/`
- **Redis**: `~/supplynexus/infrastructure/redis/data-prod/`

**重要提示：**
- 定期备份这些目录
- 确保有足够的磁盘空间
- 设置适当的文件权限

## ❓ 故障排查

### PostgreSQL 无法启动

```bash
# 查看详细日志
cd ~/supplynexus/infrastructure/postgresql
docker-compose logs postgresql

# 检查端口是否被占用
sudo netstat -tulpn | grep 5435

# 检查数据目录权限
ls -la ./data-prod
```

### Redis 无法启动

```bash
# 查看详细日志
cd ~/supplynexus/infrastructure/redis
docker-compose logs redis

# 检查端口是否被占用
sudo netstat -tulpn | grep 6382

# 检查数据目录权限
ls -la ./data-prod
```

### 连接被拒绝

1. 检查防火墙设置
2. 检查容器是否正在运行：`docker ps`
3. 检查端口映射是否正确：`docker-compose ps`
4. 检查密码是否正确

## 📚 更多信息

- PostgreSQL 详细配置: `deployment/docker/postgresql/README.md`
- 项目主 README: `README.md`
- 部署架构说明: `deployment/ARCHITECTURE.md`

---

**提示**: 如果遇到问题，请查看容器日志获取详细错误信息。
