#!/bin/bash

# 密钥对生成工具脚本
# 用法: ./generate_keys.sh <tenant_name> [options]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 显示帮助信息
show_help() {
    echo -e "${BLUE}密钥对生成工具${NC}"
    echo
    echo "用法:"
    echo "  $0 <tenant_name> [options]"
    echo
    echo "参数:"
    echo "  tenant_name    租户名称 (例如: impeach)"
    echo
    echo "选项:"
    echo "  --type TYPE     密钥类型 (默认: rsa)"
    echo "  --size SIZE     密钥大小 (默认: 2048)"
    echo "  --save-db       保存公钥到数据库"
    echo "  --output-dir DIR 输出目录 (默认: ./keys)"
    echo "  --display       显示生成的密钥"
    echo "  --help          显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0 impeach --save-db"
    echo "  $0 test_tenant --type rsa --size 4096 --output-dir ./custom_keys"
    echo "  $0 demo_tenant --save-db --output-dir ./tenant_keys --display"
    echo
}

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}检查依赖...${NC}"
    
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 未安装${NC}"
        exit 1
    fi
    
    # 检查虚拟环境
    if [[ ! -f "$BACKEND_DIR/.venv/bin/activate" ]]; then
        echo -e "${RED}❌ 虚拟环境不存在，请先运行: cd $BACKEND_DIR && python -m venv .venv${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 依赖检查通过${NC}"
    echo
}

# 激活虚拟环境
activate_venv() {
    echo -e "${BLUE}激活虚拟环境...${NC}"
    source "$BACKEND_DIR/.venv/bin/activate"
    echo -e "${GREEN}✅ 虚拟环境已激活${NC}"
    echo
}

# 检查 Python 包
check_python_packages() {
    echo -e "${BLUE}检查 Python 包...${NC}"
    
    # 检查必要的包
    local required_packages=("cryptography" "sqlalchemy" "asyncpg")
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  缺少以下 Python 包: ${missing_packages[*]}${NC}"
        echo -e "${BLUE}正在安装...${NC}"
        pip install "${missing_packages[@]}"
        echo -e "${GREEN}✅ Python 包安装完成${NC}"
    else
        echo -e "${GREEN}✅ Python 包检查通过${NC}"
    fi
    echo
}

# 创建 .gitignore 文件
create_gitignore() {
    local output_dir="$1"
    local gitignore_file="$output_dir/.gitignore"
    
    if [[ ! -f "$gitignore_file" ]]; then
        echo -e "${BLUE}创建 .gitignore 文件...${NC}"
        cat > "$gitignore_file" << EOF
# 密钥文件 - 不要提交到版本控制
*.pem
*.key
*.crt
*.p12
*.pfx

# 但保留 .gitignore 文件本身
!.gitignore
EOF
        echo -e "${GREEN}✅ .gitignore 文件已创建: $gitignore_file${NC}"
        echo
    fi
}

# 主函数
main() {
    # 检查参数
    if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
        show_help
        exit 0
    fi
    
    # 获取租户名称
    local tenant_name="$1"
    shift
    
    # 检查租户名称
    if [[ -z "$tenant_name" ]]; then
        echo -e "${RED}❌ 错误: 请提供租户名称${NC}"
        show_help
        exit 1
    fi
    
    echo -e "${GREEN}🚀 开始生成密钥对${NC}"
    echo -e "${BLUE}租户: $tenant_name${NC}"
    echo
    
    # 检查依赖
    check_dependencies
    
    # 激活虚拟环境
    activate_venv
    
    # 检查 Python 包
    check_python_packages
    
    # 切换到后端目录
    cd "$BACKEND_DIR"
    
    # 构建 Python 命令
    local python_cmd="python scripts/generate_keys.py $tenant_name"
    
    # 添加其他参数
    while [[ $# -gt 0 ]]; do
        python_cmd="$python_cmd $1"
        shift
    done
    
    # 执行 Python 脚本
    echo -e "${BLUE}执行密钥生成...${NC}"
    echo "命令: $python_cmd"
    echo
    
    if eval "$python_cmd"; then
        echo -e "${GREEN}🎯 密钥生成成功！${NC}"
        
        # 如果指定了输出目录，创建 .gitignore
        for arg in "$@"; do
            if [[ "$arg" == "--output-dir" ]]; then
                local output_dir="$2"
                create_gitignore "$output_dir"
                break
            fi
        done
        
        exit 0
    else
        echo -e "${RED}❌ 密钥生成失败${NC}"
        exit 1
    fi
}

# 运行主函数
main "$@"
