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

# 编辑配置文件，修改密码
vi .env
```

### 3. 启动服务

```bash
# 启动 PostgreSQL
docker-compose up -d

# 检查状态
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

数据存储在 `./data` 目录中，确保：
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
