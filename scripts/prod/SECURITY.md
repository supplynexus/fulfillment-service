# 生产环境安全配置说明

## ⚠️ 重要安全提醒

**生产环境配置文件包含敏感信息，绝对不要提交到 Git！**

## 被忽略的敏感文件

以下文件包含真实的密码、密钥和服务器信息，已被 `.gitignore` 忽略：

- `deployment/environments/env.prod` - 后端环境配置（包含数据库密码、Redis 密码、API 密钥等）
- `deployment/environments/frontend/env.prod` - 前端环境配置
- `docker-compose.prod.yml` - 生产环境 Docker Compose 配置（包含密码引用）

## 安全最佳实践

### 1. 配置文件管理

- ✅ **正确做法**：配置文件只存在于服务器上，通过安全方式传输（如 `scp`、`rsync`）
- ❌ **错误做法**：将配置文件提交到 Git 仓库

### 2. 密钥轮换

如果发现密钥已泄露：
1. 立即轮换所有密钥（数据库密码、Redis 密码、API 密钥等）
2. 更新服务器上的配置文件
3. 重启相关服务

### 3. 访问控制

- 配置文件应设置适当的文件权限：`chmod 600 deployment/environments/env.prod`
- 只有必要的用户才能访问这些文件

### 4. 备份安全

- 备份文件时，确保备份存储位置安全
- 不要将备份文件上传到公共存储

## 配置文件位置

生产环境配置文件应存储在服务器上：
- 服务器路径：`/opt/supplynexus/deployment/environments/`
- 本地开发：这些文件不应存在于本地仓库中

## 如果文件已被提交

如果发现敏感文件已被提交到 Git：

1. **立即轮换所有密钥和密码**
2. 从 Git 历史中移除文件：
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch deployment/environments/env.prod docker-compose.prod.yml" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. 强制推送到远程仓库（需要团队协调）
4. 通知所有团队成员重新克隆仓库

## 验证配置

定期检查确保敏感文件未被跟踪：

```bash
# 检查文件是否被忽略
git check-ignore -v deployment/environments/env.prod
git check-ignore -v docker-compose.prod.yml

# 检查是否有未跟踪的敏感文件
git status | grep -E "(env\.prod|docker-compose\.prod)"
```
