# 部署文档索引

本文档提供各环境的部署流程索引。

## 📚 部署文档

### Develop 分支 → Dev 环境

**文档位置**: [`scripts/dev/DEPLOYMENT.md`](../scripts/dev/DEPLOYMENT.md)

**适用场景**: 将 `develop` 分支的代码部署到 dev 环境（https://admin.dev.supplynexus.store）

**快速部署**:
```bash
ssh ubuntu@133.242.179.110
cd /opt/supplynexus
./scripts/dev/deploy-from-git.sh
```

### Main 分支 → Prod 环境

**文档位置**: [`scripts/prod/DEPLOYMENT_STEPS.md`](../scripts/prod/DEPLOYMENT_STEPS.md)

**适用场景**: 将 `main` 分支的代码部署到生产环境（https://admin.supplynexus.store）

**快速部署**:
```bash
ssh ubuntu@133.242.179.110
cd /opt/supplynexus
./scripts/prod/deploy-from-git.sh
```

## 🌍 环境对应关系

| 分支 | 环境 | 域名 | Docker Compose |
|------|------|------|----------------|
| `develop` | Dev 环境 | https://admin.dev.supplynexus.store | `docker-compose.dev.yml` |
| `main` | Prod 环境 | https://admin.supplynexus.store | `docker-compose.prod.yml` |

## 🔄 部署流程概览

### Develop 分支部署流程

1. 在 GitHub 上将 PR merge 到 `develop` 分支
2. SSH 到服务器执行部署脚本
3. 脚本自动拉取代码、同步文件、运行迁移、重启服务

### Main 分支部署流程

1. 在 GitHub 上将 PR merge 到 `main` 分支
2. SSH 到服务器执行部署脚本
3. 脚本自动拉取代码、同步文件、运行迁移、重启服务

## 📝 注意事项

- **数据持久化**: 所有环境的数据库和 Redis 数据都存储在 Docker volumes 中，不会因代码更新而丢失
- **环境配置**: 生产环境的配置文件包含敏感信息，不会提交到 Git
- **服务端口**: Dev 和 Prod 环境使用不同的端口，避免冲突
- **部署脚本**: 所有部署脚本都位于 `scripts/{env}/deploy-from-git.sh`

## 🔍 故障排查

如果遇到部署问题，请参考对应环境的部署文档中的故障排查部分。

## 📞 相关文档

- [Git 工作流规范](./GIT_WORKFLOW.md)
- [环境配置快速参考](./ENVIRONMENT_CONFIG_QUICK_REFERENCE.md)
- [本地开发环境搭建](./DEVELOPMENT.md)
