#!/bin/bash

# SupplyNexus OMS Work Resume Script
# Usage: ./scripts/resume_work.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎯 SupplyNexus OMS 工作恢复脚本${NC}"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "backend/app/main.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Show current git status
echo -e "\n${BLUE}📋 当前Git状态:${NC}"
CURRENT_BRANCH=$(git branch --show-current)
echo -e "当前分支: ${YELLOW}$CURRENT_BRANCH${NC}"

# Show recent commits
echo -e "\n${BLUE}📝 最近提交:${NC}"
git log --oneline -5

# Show current progress
echo -e "\n${BLUE}📊 当前进度:${NC}"
if [ -f "docs/PROGRESS_LOG.md" ]; then
    echo -e "${GREEN}✅ 找到进度日志${NC}"
    echo -e "\n${YELLOW}最近进度更新:${NC}"
    tail -5 docs/PROGRESS_LOG.md | grep -A 5 "进度更新"
else
    echo -e "${RED}❌ 未找到进度日志${NC}"
fi

# Show current task from memory
echo -e "\n${BLUE}🎯 当前任务状态:${NC}"
if [ -f ".serena/memories/current_development_progress.md" ]; then
    echo -e "${GREEN}✅ 找到进度记忆${NC}"
    echo -e "\n${YELLOW}当前任务:${NC}"
    grep -A 3 "当前任务" .serena/memories/current_development_progress.md || echo "未找到当前任务信息"
else
    echo -e "${RED}❌ 未找到进度记忆${NC}"
fi

# Show available branches
echo -e "\n${BLUE}🌿 可用分支:${NC}"
git branch -a | grep "feature/phase-" | head -5

# Show next steps
echo -e "\n${BLUE}📋 下一步建议:${NC}"
if [[ $CURRENT_BRANCH == feature/* ]]; then
    echo -e "${YELLOW}1. 继续在当前分支开发${NC}"
    echo -e "${YELLOW}2. 查看当前任务详情${NC}"
    echo -e "${YELLOW}3. 更新进度状态${NC}"
elif [[ $CURRENT_BRANCH == develop ]]; then
    echo -e "${YELLOW}1. 切换到工作分支${NC}"
    echo -e "${YELLOW}2. 或创建新的功能分支${NC}"
elif [[ $CURRENT_BRANCH == main ]]; then
    echo -e "${RED}⚠️  当前在主分支，建议切换到develop${NC}"
    echo -e "${YELLOW}1. git checkout develop${NC}"
    echo -e "${YELLOW}2. 继续开发工作${NC}"
fi

# Show quick commands
echo -e "\n${BLUE}⚡ 快速命令:${NC}"
echo "  查看任务: ./scripts/show_tasks.sh"
echo "  更新进度: ./scripts/update_progress.sh <phase> <issue> <status>"
echo "  创建分支: ./scripts/create_feature_branch.sh <phase> <feature>"
echo "  查看文档: cat docs/DEVELOPMENT_TASKS.md"

# Check if there are uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "\n${YELLOW}⚠️  有未提交的更改:${NC}"
    git status --short
    echo -e "\n${BLUE}建议:${NC}"
    echo "  1. git add ."
    echo "  2. git commit -m 'feat: your commit message'"
fi

echo -e "\n${GREEN}✅ 工作状态检查完成${NC}"
