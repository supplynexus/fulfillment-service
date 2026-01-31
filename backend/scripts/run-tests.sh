#!/bin/bash

# 后端测试运行脚本
# 支持不同类型的测试：unit, integration, all

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${2}${1}${NC}"
}

# 检查参数
if [ $# -eq 0 ]; then
    print_message "用法: $0 [unit|integration|all]" $YELLOW
    print_message "  unit        - 运行单元测试" $GREEN
    print_message "  integration - 运行集成测试" $GREEN
    print_message "  all         - 运行所有测试" $GREEN
    exit 1
fi

TEST_TYPE=$1

# 运行单元测试
run_unit_tests() {
    print_message "🧪 运行后端单元测试..." $YELLOW
    python -m pytest tests/unit/ -v --cov=app --cov-report=html:htmlcov --cov-report=term-missing
}

# 运行集成测试
run_integration_tests() {
    print_message "🔗 运行后端集成测试..." $YELLOW
    python -m pytest tests/integration/ -v --cov=app --cov-report=html:htmlcov --cov-report=term-missing
}

# 运行所有测试
run_all_tests() {
    print_message "🚀 运行所有后端测试..." $YELLOW
    python -m pytest tests/ -v --cov=app --cov-report=html:htmlcov --cov-report=term-missing
}

# 根据参数执行相应测试
case $TEST_TYPE in
    "unit")
        run_unit_tests
        ;;
    "integration")
        run_integration_tests
        ;;
    "all")
        run_all_tests
        ;;
    *)
        print_message "未知的测试类型: $TEST_TYPE" $RED
        exit 1
        ;;
esac

print_message "✅ 后端测试完成!" $GREEN
