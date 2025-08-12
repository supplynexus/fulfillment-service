# 🚀 SupplyNexus OMS 开发工作流

## 📋 概述
本文档描述了SupplyNexus OMS项目的开发工作流程，包括分支策略、任务管理和代码提交规范。

## 🤝 开发约定

### Git操作和PR管理约定
- **AI助手负责**: `git commit` 和 `git push` 到feature分支
- **开发者负责**: 在GitHub网页上创建PR、review和merge到develop分支
- **避免操作**: AI助手避免不必要的merge操作，特别是merge feature分支到develop
- **开发节奏**: AI助手要控制开发节奏，每个阶段完成后要询问下一步
- **中断恢复**: 会话中断后，AI助手会检查进度并从断点继续

### 分支使用策略
AI助手需要根据以下规则判断使用哪个分支：

#### 继续使用现有feature分支的情况
- 当前feature分支还有未完成的任务
- 正在开发同一个功能的不同部分
- 需要修复当前功能的问题

#### 创建新feature分支的情况
- 当前feature分支的任务已完成并已merge
- 开始新的功能开发
- 切换到不同阶段的任务

#### 分支切换流程
1. **PR merge后**: 切换到develop分支，拉取最新代码
2. **继续开发**: 如果还有未完成任务，继续使用原feature分支
3. **新任务**: 如果开始新任务，从develop创建新的feature分支
4. **判断依据**: 根据当前任务状态和开发进度决定

---

## 🌿 分支策略

### 分支类型
1. **main** - 生产环境代码，稳定版本
2. **develop** - 开发环境代码，集成所有功能
3. **feature/phase-{phase}-{task-name}** - 功能开发分支
4. **fix/{issue-description}** - 问题修复分支
5. **hotfix/{issue-description}** - 热修复分支

### 分支命名规范
- Feature分支: `feature/phase-{phase-number}-{task-name}`
- Bug修复: `fix/{issue-description}`
- 热修复: `hotfix/{issue-description}`

## 📝 开发流程

### 1. 开始新功能开发

```bash
# 确保在develop分支
git checkout develop
git pull origin develop

# 使用脚本创建新功能分支
./scripts/create_feature_branch.sh <phase> <feature-name>

# 例如：创建Phase 1的JWT认证系统分支
./scripts/create_feature_branch.sh 1 jwt-auth-system
```

### 2. 开发过程中的提交

```bash
# 添加文件
git add .

# 提交代码（使用规范的提交信息）
git commit -m "feat: implement JWT token generation"
git commit -m "fix: resolve authentication middleware issue"
git commit -m "docs: update API documentation"
```

### 3. 完成功能开发

```bash
# 推送分支到远程
git push -u origin feature/phase-1-jwt-auth-system

# 创建Pull Request
# 在GitHub/GitLab上创建PR，从feature分支到develop分支
```

### 4. 代码审查和合并

1. AI助手提供PR信息（分支、标题、描述）
2. 开发者在GitHub上创建Pull Request
3. 进行代码审查
4. 解决审查意见
5. 合并到develop分支
6. 删除功能分支

### PR信息规范
当AI助手完成一个阶段的工作并推送分支后，必须提供以下PR信息：

**PR分支**: `feature/phase-{phase}-{task-name}` → `develop`

**PR标题**: `feat: {phase description} - {task description}`

**PR描述**:
```
## 🎯 功能概述
{简要描述本次PR实现的功能}

## 📋 包含内容
- [ ] {具体功能点1}
- [ ] {具体功能点2}
- [ ] {具体功能点3}

## 🔧 技术实现
- {技术实现要点1}
- {技术实现要点2}

## 🧪 测试
- [ ] {测试项目1}
- [ ] {测试项目2}

## 📚 文档更新
- [ ] {文档更新1}
- [ ] {文档更新2}

## 🔄 下一步计划
{下一步要做什么}
```

## 🎯 任务管理

### 查看任务状态
```bash
# 查看所有任务状态
./scripts/show_tasks.sh

# 查看特定阶段的任务
./scripts/show_tasks.sh 1
```

### 任务分解
项目分为5个阶段，每个阶段包含多个功能：

#### Phase 1: 认证和安全基础
- JWT认证系统完善
- API Key管理系统

#### Phase 2: 数据获取和同步
- Shopify API集成
- 批量数据同步

#### Phase 3: 核心业务功能
- 订单管理API
- 前端订单界面
- 自动发货配置

#### Phase 4: 用户界面
- 仪表板界面
- 订单管理界面
- 商品管理界面
- 发货操作界面
- 库存管理界面

#### Phase 5: 多租户完善
- 租户隔离机制
- 租户配置管理
- 租户权限管理

## 📋 提交规范

### 提交类型
- **feat**: 新功能
- **fix**: 修复bug
- **docs**: 文档更新
- **style**: 代码格式调整
- **refactor**: 代码重构
- **test**: 测试相关
- **chore**: 构建过程或辅助工具的变动

### 提交信息格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### 示例
```
feat(auth): implement JWT token generation

- Add JWT token creation with configurable expiration
- Implement token validation middleware
- Add refresh token functionality

Closes #123
```

## 🧪 测试要求

### 后端测试
- 每个API接口都要有单元测试
- 关键业务逻辑要有集成测试
- 数据库操作要有测试覆盖

### 前端测试
- 每个组件都要有组件测试
- 关键用户交互要有E2E测试
- 工具函数要有单元测试

### 测试命令
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

## 📚 文档要求

### 必须更新的文档
- API文档（Swagger/OpenAPI）
- 数据库迁移文档
- 部署流程文档
- 用户使用手册

### 文档位置
- API文档: `backend/docs/`
- 数据库文档: `docs/backup/`
- 部署文档: `docs/deployment/`
- 开发文档: `docs/dev/`

## 🔧 开发环境设置

### 后端环境
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 前端环境
```bash
cd frontend
npm install
```

### 数据库设置
```bash
# 使用Docker启动PostgreSQL
docker-compose up -d postgresql

# 运行数据库迁移
cd backend
alembic upgrade head
```

## 🚀 部署流程

### 开发环境部署
```bash
# 启动所有服务
docker-compose -f docker-compose.dev.yml up -d

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

### 生产环境部署
```bash
# 使用部署脚本
./scripts/deployment/deploy.sh production
```

## 📞 问题报告

### Bug报告
1. 在GitHub/GitLab上创建Issue
2. 使用bug模板
3. 提供详细的复现步骤
4. 包含错误日志和截图

### 功能请求
1. 在GitHub/GitLab上创建Issue
2. 使用feature request模板
3. 描述功能需求和用例
4. 讨论实现方案

## 🤝 代码审查

### 审查要点
- 代码质量和可读性
- 功能完整性
- 测试覆盖度
- 文档更新
- 安全性考虑

### 审查流程
1. 创建Pull Request
2. 自动运行CI/CD检查
3. 代码审查员审查代码
4. 解决审查意见
5. 获得批准后合并

## 📈 项目进度跟踪

### 进度更新
- 每周更新任务状态
- 记录完成的功能
- 更新项目文档
- 分享进度报告

### 里程碑
- Phase 1: 认证系统完成
- Phase 2: 数据同步完成
- Phase 3: 核心功能完成
- Phase 4: 用户界面完成
- Phase 5: 多租户完成

## 🔒 安全考虑

### 代码安全
- 定期更新依赖包
- 进行安全扫描
- 遵循安全编码规范
- 保护敏感信息

### 数据安全
- 加密敏感数据
- 实现访问控制
- 记录审计日志
- 定期备份数据
