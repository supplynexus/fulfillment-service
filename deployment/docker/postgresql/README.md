# PostgreSQL 独立部署配置

## 📋 说明

这是 SupplyNexus 项目的 PostgreSQL 数据库独立部署配置，用于在服务器上单独运行 PostgreSQL 服务。

## 🚀 使用方法

### 1. 复制文件到服务器

将此目录下的文件复制到服务器：

```bash
# 在服务器上创建目录
mkdir -p ~/docker/postgresql
cd ~/docker/postgresql

# 复制配置文件
# - docker-compose.yml
# - environment.example (重命名为 .env)
```

### 2. 配置环境变量

```bash
# 复制环境配置
cp environment.example .env

# 编辑配置文件，修改密码和环境设置
vi .env

# 根据部署环境调整容器名称：
# 开发环境：CONTAINER_NAME=supplynexus-postgres-dev
# 测试环境：CONTAINER_NAME=supplynexus-postgres-stg  
# 生产环境：CONTAINER_NAME=supplynexus-postgres-prod
```

### 3. 启动服务

#### **推荐方式：使用部署脚本**
```bash
# 一键部署指定环境
./deploy.sh dev      # 开发环境
./deploy.sh stg  # 测试环境
./deploy.sh prod     # 生产环境
```

#### **手动方式：使用默认 .env 文件**
```bash
# 复制对应环境的配置
cp environment.dev .env     # 开发环境
cp environment.stg .env # 测试环境  
cp environment.prod .env    # 生产环境

# 编辑密码（重要！）
vi .env

# 启动服务
docker-compose up -d
```

#### **检查状态**
```bash
docker-compose ps
docker-compose logs postgresql
```

### 4. 验证连接

```bash
# 进入容器测试
docker-compose exec postgresql psql -U supplynexus_admin -d supplynexus

# 或使用外部工具连接
# Host: your-server-ip
# Port: 5433
# Database: supplynexus
# Username: supplynexus_admin
# Password: (您设置的密码)
```

## 📁 数据持久化

数据存储在环境特定目录中，避免冲突：

- **开发环境**: `./data-dev/`
- **测试环境**: `./data-stg/`  
- **生产环境**: `./data-prod/`

每个环境的数据完全独立，可以在同一服务器上安全运行多个环境。

确保：
- 定期备份数据目录
- 设置适当的文件权限
- 监控磁盘空间

## 🔧 连接字符串

应用连接时使用：

```
postgresql://supplynexus_admin:your-password@your-server-ip:5433/supplynexus
```

## 🛡️ 安全建议

1. 修改默认密码
2. 限制网络访问（防火墙规则）
3. 定期更新 PostgreSQL 镜像
4. 设置适当的用户权限
