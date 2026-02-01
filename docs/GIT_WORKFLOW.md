# Git 工作流规范

本文档定义了 SupplyNexus Fulfillment Service 项目的 Git 工作流规范，所有团队成员必须遵循。

## 📋 目录

- [禁止直接提交到保护分支](#禁止直接提交到保护分支)
- [正确的 Git 工作流](#正确的-git-工作流)
- [分支与环境对应关系](#分支与环境对应关系)
- [检查点](#检查点)
- [常见问题](#常见问题)

## 🚫 禁止直接提交到保护分支

- **禁止直接提交到 `develop` 分支**
- **禁止直接提交到 `main` 分支**
- **所有更改必须通过 Pull Request 流程**

## ✅ 正确的 Git 工作流

### 1. 始终从 `develop` 创建功能分支

- 每次程序变更都必须从 `develop` 分支创建新的功能分支
- 分支命名规范：
  - 功能开发：`feature/功能名称`
  - Bug 修复：`fix/修复内容`
  - 示例：
    - `feature/environment-badge`
    - `fix/alembic-migration-constraint-check`

### 2. 在功能分支上进行更改

- 在功能分支上提交所有更改
- 使用清晰的提交信息
- 提交信息格式：
  ```
  type: 简短描述

  详细说明（可选）
  ```
  
  类型包括：
  - `feat`: 新功能
  - `fix`: Bug 修复
  - `docs`: 文档更新
  - `style`: 代码格式调整
  - `refactor`: 代码重构
  - `test`: 测试相关
  - `chore`: 构建/工具相关

### 3. 创建 PR 到 `develop`

- 推送功能分支到远程仓库：
  ```bash
  git push -u origin feature/功能名称
  ```
- 创建 Pull Request 到 `develop` 分支
- 等待代码审核和合并
- PR 标题应清晰描述更改内容
- PR 描述应包含：
  - 更改的目的和背景
  - 主要更改内容
  - 测试情况
  - 相关 Issue（如有）

### 4. develop -> main 的 PR

- **重要**：`develop` -> `main` 的 PR 由项目维护者手动创建
- AI 助手不会自动创建 `develop` -> `main` 的 PR
- 只有经过充分测试和验证的代码才能合并到 `main` 分支
- 合并到 `main` 前必须确保：
  - 所有测试通过
  - 代码审核完成
  - 在 dev 环境验证通过

## 🌍 分支与环境对应关系

| 分支 | 环境 | 域名 | 说明 |
|------|------|------|------|
| `develop` | Dev 环境 | https://admin.dev.supplynexus.store | 开发测试环境 |
| `main` | Prod 环境 | https://admin.supplynexus.store | 生产环境 |

### 重要规则

- **`develop` 分支的代码部署到 dev 环境**
  - 用于开发和测试新功能
  - 允许快速迭代和实验
  - 可以包含未完全稳定的功能

- **`main` 分支的代码部署到 prod 环境**
  - 只包含经过充分测试的稳定代码
  - 所有功能开发都在 `develop` 分支上进行
  - 只有经过测试验证的代码才能合并到 `main` 分支

### 环境域名

- **Dev 环境**：
  - 前端：https://admin.dev.supplynexus.store
  - API：https://api.dev.supplynexus.store

- **Prod 环境**：
  - 前端：https://admin.supplynexus.store
  - API：https://api.supplynexus.store

## ✅ 检查点

在每次提交和创建 PR 前，请检查以下事项：

- [ ] 在提交前检查当前分支
- [ ] 确保不在 `develop` 或 `main` 分支上直接提交
- [ ] 如果当前在保护分支，提醒创建功能分支
- [ ] 创建 PR 时，目标分支必须是 `develop`（除非用户明确指定其他分支）
- [ ] **绝对不要**自动创建 `develop` -> `main` 的 PR
- [ ] 确保提交信息清晰明确
- [ ] 确保代码已通过本地测试

## 🔄 完整工作流示例

### 示例：开发新功能

```bash
# 1. 确保在 develop 分支并拉取最新代码
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/user-profile

# 3. 进行开发和提交
git add .
git commit -m "feat: 添加用户个人资料页面"

# 4. 推送分支
git push -u origin feature/user-profile

# 5. 在 GitHub 上创建 PR 到 develop 分支
# 等待代码审核和合并
```

### 示例：修复 Bug

```bash
# 1. 从 develop 创建修复分支
git checkout develop
git pull origin develop
git checkout -b fix/login-error

# 2. 修复并提交
git add .
git commit -m "fix: 修复登录时的认证错误"

# 3. 推送并创建 PR
git push -u origin fix/login-error
```

## ❓ 常见问题

### Q: 如果我在 `develop` 分支上做了更改怎么办？

A: 如果更改还未提交：
```bash
# 保存更改到 stash
git stash

# 创建功能分支
git checkout -b feature/your-feature

# 恢复更改
git stash pop
```

如果更改已提交：
```bash
# 创建新分支包含这些提交
git checkout -b feature/your-feature

# 在 develop 分支上重置
git checkout develop
git reset --hard origin/develop
```

### Q: 可以同时创建多个功能分支吗？

A: 可以，但建议：
- 一次专注于一个功能
- 完成一个功能的 PR 后再开始下一个
- 如果必须并行开发，确保分支之间没有冲突

### Q: 如何更新功能分支？

A: 如果 `develop` 分支有新的提交，需要更新你的功能分支：
```bash
# 在功能分支上
git checkout feature/your-feature

# 合并 develop 的最新更改
git merge develop

# 或者使用 rebase（更推荐）
git rebase develop
```

### Q: PR 被拒绝后怎么办？

A: 
1. 根据反馈修改代码
2. 在功能分支上提交新的更改
3. 推送更新，PR 会自动更新

### Q: 如何撤销一个 PR？

A: 在 GitHub 上关闭 PR，然后删除功能分支：
```bash
git checkout develop
git branch -d feature/your-feature
git push origin --delete feature/your-feature
```

## 📚 相关文档

- [部署指南](./DEPLOYMENT.md) - 环境部署说明
- [开发指南](./DEVELOPMENT.md) - 开发环境设置
- [快速开始](./QUICK_START.md) - 项目快速开始指南

## 🔗 相关链接

- [GitHub 仓库](https://github.com/supplynexus/fulfillment-service)
- Dev 环境：https://admin.dev.supplynexus.store
- Prod 环境：https://admin.supplynexus.store

---

**最后更新**: 2026-02-01  
**维护者**: SupplyNexus Team
