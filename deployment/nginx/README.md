# Nginx 部署说明

## 概述

本目录包含适用于 Ubuntu 系统上 Nginx 的配置文件。这些配置文件用于代理 SupplyNexus 后端 API 服务。

## 文件说明

- `backend.conf` - 后端 API 的 Nginx 配置样本
- `api.dev.supplynexus.store.conf` - 开发环境 API 服务配置
- `api.supplynexus.store.conf` - 生产环境 API 服务配置
- `admin.supplynexus.store.conf` - 生产环境前端管理后台配置
- `README.md` - 本说明文档

## 部署步骤

### 1. 复制配置文件

```bash
# 复制配置文件到 Nginx sites-available 目录
sudo cp backend.conf /etc/nginx/sites-available/supplynexus-backend

# 创建软链接到 sites-enabled 目录
sudo ln -s /etc/nginx/sites-available/supplynexus-backend /etc/nginx/sites-enabled/
```

### 2. 修改配置

编辑配置文件，根据实际情况修改以下内容：

```bash
sudo nano /etc/nginx/sites-available/supplynexus-backend
```

**需要修改的配置项：**

1. **域名**：
   ```nginx
   server_name api.dev.supplynexus.store;  # 修改为实际域名
   ```

2. **SSL 证书路径**：
   ```nginx
   ssl_certificate /etc/letsencrypt/live/api.dev.supplynexus.store/fullchain.pem;
   ssl_certificate_key /etc/letsencrypt/live/api.dev.supplynexus.store/privkey.pem;
   ```

3. **后端服务地址**：
   ```nginx
   upstream backend_api {
       server 127.0.0.1:8000;  # 修改为实际的后端服务地址和端口
   }
   ```

4. **日志文件路径**：
   ```nginx
   access_log /var/log/nginx/api.dev.supplynexus.store.access.log;
   error_log /var/log/nginx/api.dev.supplynexus.store.error.log;
   ```

### 3. 申请 SSL 证书

使用 Let's Encrypt 申请 SSL 证书：

```bash
# 安装 certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# 申请证书
sudo certbot --nginx -d api.dev.supplynexus.store

# 或者手动申请（如果 Nginx 配置有问题）
sudo certbot certonly --standalone -d api.dev.supplynexus.store
```

### 4. 测试配置

```bash
# 测试 Nginx 配置语法
sudo nginx -t

# 如果测试通过，重新加载配置
sudo systemctl reload nginx
```

### 5. 启动服务

```bash
# 启动 Nginx（如果未启动）
sudo systemctl start nginx

# 设置开机自启
sudo systemctl enable nginx

# 检查服务状态
sudo systemctl status nginx
```

## 配置说明

### 主要特性

1. **HTTP 到 HTTPS 重定向** - 自动将 HTTP 请求重定向到 HTTPS
2. **SSL/TLS 安全配置** - 使用强加密套件和安全头
3. **健康检查支持** - 提供健康检查端点
4. **缓存控制** - 针对不同端点设置合适的缓存策略
5. **负载均衡准备** - 支持多后端服务器配置
6. **详细日志** - 记录访问和错误日志

### 安全配置

- 强制 HTTPS
- 安全头配置（HSTS、XSS 保护等）
- SSL 协议和加密套件限制
- 客户端请求大小限制

### 性能优化

- 连接保持（keepalive）
- 代理缓冲配置
- 静态文件缓存
- 超时设置优化

## 故障排除

### 常见问题

1. **配置语法错误**
   ```bash
   sudo nginx -t
   ```

2. **SSL 证书问题**
   ```bash
   # 检查证书状态
   sudo certbot certificates
   
   # 续期证书
   sudo certbot renew --dry-run
   ```

3. **权限问题**
   ```bash
   # 检查 Nginx 用户权限
   sudo -u www-data nginx -t
   
   # 修复日志文件权限
   sudo chown www-data:www-data /var/log/nginx/api.dev.supplynexus.store.*.log
   ```

4. **端口冲突**
   ```bash
   # 检查端口占用
   sudo netstat -tlnp | grep :80
   sudo netstat -tlnp | grep :443
   ```

### 日志查看

```bash
# 查看访问日志
sudo tail -f /var/log/nginx/api.dev.supplynexus.store.access.log

# 查看错误日志
sudo tail -f /var/log/nginx/api.dev.supplynexus.store.error.log

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log
```

### 健康检查

```bash
# 测试健康检查端点
curl -I https://api.dev.supplynexus.store/health

# 测试 API 端点
curl -I https://api.dev.supplynexus.store/api/v1/health
```

## 维护

### 定期任务

1. **SSL 证书续期**
   ```bash
   # 添加到 crontab
   sudo crontab -e
   
   # 添加以下行（每天凌晨 2 点检查续期）
   0 2 * * * /usr/bin/certbot renew --quiet
   ```

2. **日志轮转**
   ```bash
   # 配置 logrotate
   sudo nano /etc/logrotate.d/supplynexus-backend
   ```

3. **配置备份**
   ```bash
   # 备份配置文件
   sudo cp /etc/nginx/sites-available/supplynexus-backend /etc/nginx/sites-available/supplynexus-backend.backup
   ```

### 监控

建议配置监控来检查：
- Nginx 服务状态
- SSL 证书有效期
- 后端服务健康状态
- 错误日志数量
- 响应时间

## 注意事项

1. **防火墙配置** - 确保开放 80 和 443 端口
2. **SELinux** - 如果使用 SELinux，可能需要配置相应的策略
3. **备份** - 定期备份配置文件和 SSL 证书
4. **更新** - 定期更新 Nginx 和 SSL 证书工具
5. **安全** - 定期检查安全配置和日志
