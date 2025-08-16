# User Management Tool

这个工具用于管理 SupplyNexus Fulfillment Service 的用户账户。它提供了安全的密码哈希和用户管理功能。

## 功能特性

- ✅ **安全的密码哈希**: 使用 bcrypt 算法，每个密码都有唯一的盐值
- ✅ **密码强度验证**: 确保密码符合安全要求
- ✅ **用户管理**: 创建、更新、查看、删除用户
- ✅ **安全日志**: 记录密码修改和登录尝试
- ✅ **账户锁定**: 防止暴力破解攻击

## 安装和设置

### 前置要求

1. Python 3.8+
2. 虚拟环境已激活
3. 数据库已运行
4. 依赖包已安装

### 环境检查

```bash
# 检查虚拟环境
source .venv/bin/activate

# 检查依赖
pip install -r requirements.txt
```

## 使用方法

### Shell 脚本 (推荐)

```bash
# 查看帮助
./scripts/user_manager.sh help

# 创建用户
./scripts/user_manager.sh create admin@example.com MySecurePass123! --full-name "Admin User"

# 更新密码
./scripts/user_manager.sh update admin@example.com NewSecurePass123!

# 列出所有用户
./scripts/user_manager.sh list

# 查看用户详情
./scripts/user_manager.sh show admin@example.com

# 删除用户
./scripts/user_manager.sh delete admin@example.com
```

### Python 脚本 (直接使用)

```bash
# 查看帮助
python scripts/user_manager.py --help

# 创建用户
python scripts/user_manager.py create admin@example.com MySecurePass123! --full-name "Admin User"

# 更新密码
python scripts/user_manager.py update admin@example.com NewSecurePass123!

# 列出所有用户
python scripts/user_manager.py list

# 查看用户详情
python scripts/user_manager.py show admin@example.com

# 删除用户
python scripts/user_manager.py delete admin@example.com
```

## 密码要求

密码必须满足以下安全要求：

- ✅ 至少 8 个字符
- ✅ 包含至少一个大写字母
- ✅ 包含至少一个小写字母
- ✅ 包含至少一个数字
- ✅ 包含至少一个特殊字符

### 有效密码示例

```
MySecurePass123!
Admin@2024
Test#Password1
```

### 无效密码示例

```
password        # 太短，缺少大写、数字、特殊字符
Password        # 缺少数字和特殊字符
Password123     # 缺少特殊字符
```

## 安全特性

### 密码哈希

- 使用 **bcrypt** 算法
- 每个密码都有唯一的盐值
- 可配置的轮数（默认 12 轮）
- 哈希字符串包含所有必要信息

### 账户安全

- **失败登录限制**: 5 次失败后锁定 30 分钟
- **密码过期**: 可设置密码过期时间
- **登录记录**: 记录最后登录时间和失败次数
- **账户状态**: 支持激活/停用账户

### 数据库字段

用户表包含以下安全相关字段：

```sql
-- 密码安全字段
password_changed_at     -- 密码最后修改时间
password_expires_at     -- 密码过期时间
failed_login_attempts   -- 失败登录次数
locked_until           -- 账户锁定时间
last_login_at          -- 最后登录时间
```

## 错误处理

### 常见错误

1. **密码强度不足**
   ```
   ❌ Password validation failed: Password must contain at least one special character
   ```

2. **用户不存在**
   ```
   ❌ User with email 'user@example.com' not found
   ```

3. **用户已存在**
   ```
   ❌ User with email 'user@example.com' already exists
   ```

4. **数据库连接失败**
   ```
   ❌ Error creating user: connection failed
   ```

### 故障排除

1. **虚拟环境未激活**
   ```bash
   source .venv/bin/activate
   ```

2. **依赖包缺失**
   ```bash
   pip install -r requirements.txt
   ```

3. **数据库未运行**
   ```bash
   # 检查数据库状态
   docker ps | grep postgres
   ```

4. **权限问题**
   ```bash
   chmod +x scripts/user_manager.sh
   ```

## 示例工作流

### 创建管理员用户

```bash
# 1. 创建管理员用户
./scripts/user_manager.sh create admin@supplynexus.store AdminPass123! --full-name "System Administrator"

# 2. 验证用户创建
./scripts/user_manager.sh show admin@supplynexus.store

# 3. 查看所有用户
./scripts/user_manager.sh list
```

### 更新用户密码

```bash
# 1. 更新密码
./scripts/user_manager.sh update user@example.com NewSecurePass123!

# 2. 验证密码更新
./scripts/user_manager.sh show user@example.com
```

### 用户管理

```bash
# 1. 查看所有用户
./scripts/user_manager.sh list

# 2. 查看特定用户详情
./scripts/user_manager.sh show user@example.com

# 3. 删除用户（需要确认）
./scripts/user_manager.sh delete user@example.com
```

## 技术细节

### 密码哈希算法

```python
# 使用 bcrypt 进行密码哈希
import bcrypt

# 生成盐值和哈希
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

# 验证密码
is_valid = bcrypt.checkpw(password.encode('utf-8'), hashed)
```

### 数据库模型

```python
class User(Base):
    __tablename__ = "users"
    
    # 基本信息
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # 安全字段
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    password_expires_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
```

## 最佳实践

1. **定期更新密码**: 建议每 90 天更新一次密码
2. **使用强密码**: 遵循密码强度要求
3. **限制访问**: 只给必要用户管理员权限
4. **监控登录**: 定期检查失败登录记录
5. **备份数据**: 定期备份用户数据

## 支持

如果遇到问题，请检查：

1. 虚拟环境是否正确激活
2. 数据库是否正在运行
3. 依赖包是否正确安装
4. 网络连接是否正常

更多信息请参考项目文档或联系开发团队。
