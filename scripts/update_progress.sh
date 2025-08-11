#!/bin/bash

# SupplyNexus OMS Progress Updater
# Usage: ./scripts/update_progress.sh <phase> <issue> <status> [description]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -lt 3 ]; then
    echo "Usage: $0 <phase> <issue> <status> [description]"
    echo "Status options: started, completed, failed, paused"
    echo "Example: $0 1 1.1 completed 'JWT token generation implemented'"
    exit 1
fi

PHASE=$1
ISSUE=$2
STATUS=$3
DESCRIPTION=${4:-""}

# Get current timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Create progress update
PROGRESS_UPDATE="## 📍 进度更新 - $TIMESTAMP

**阶段**: Phase $PHASE
**任务**: Issue $ISSUE
**状态**: $STATUS
**描述**: $DESCRIPTION

---

"

# Append to progress file
echo "$PROGRESS_UPDATE" >> docs/PROGRESS_LOG.md

echo -e "${GREEN}✅ Progress updated!${NC}"
echo -e "${BLUE}📝 Added to docs/PROGRESS_LOG.md${NC}"
echo -e "${YELLOW}📋 Current status: Phase $PHASE, Issue $ISSUE - $STATUS${NC}"

# Show recent progress
echo -e "\n${BLUE}📊 Recent Progress:${NC}"
tail -10 docs/PROGRESS_LOG.md
