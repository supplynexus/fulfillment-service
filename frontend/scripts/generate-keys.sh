#!/bin/bash
# Generate RSA key pairs for frontend authentication
# 为前端认证生成RSA密钥对

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "${BLUE}Usage: $0 [OPTIONS]${NC}"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  --tenant-only     Generate only Tenant RSA key pair (service authentication)"
    echo "  --jwt-only        Generate only Frontend JWT key pair (browser authentication)"
    echo "  --all             Generate all key pairs (default)"
    echo "  --force           Force overwrite existing keys without confirmation"
    echo "  --help            Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0                    # Generate all keys"
    echo "  $0 --tenant-only      # Generate only tenant keys"
    echo "  $0 --jwt-only         # Generate only JWT keys"
    echo "  $0 --force            # Generate all keys, overwrite existing"
    echo ""
}

# Parse command line arguments
GENERATE_TENANT=false
GENERATE_JWT=false
FORCE_OVERWRITE=false

# Default to generate all if no arguments
if [ $# -eq 0 ]; then
    GENERATE_TENANT=true
    GENERATE_JWT=true
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --tenant-only)
            GENERATE_TENANT=true
            shift
            ;;
        --jwt-only)
            GENERATE_JWT=true
            shift
            ;;
        --all)
            GENERATE_TENANT=true
            GENERATE_JWT=true
            shift
            ;;
        --force)
            FORCE_OVERWRITE=true
            shift
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

echo -e "${BLUE}=== Frontend Key Generator ===${NC}\n"

# Create keys directory if it doesn't exist
KEYS_DIR="$(dirname "$0")/../keys"
mkdir -p "$KEYS_DIR"

echo -e "${YELLOW}📁 Keys directory: $KEYS_DIR${NC}\n"

# Function to check and overwrite key
check_and_overwrite() {
    local key_file="$1"
    local key_name="$2"
    
    if [ -f "$key_file" ]; then
        if [ "$FORCE_OVERWRITE" = true ]; then
            echo -e "${YELLOW}⚠️  $key_name exists, overwriting due to --force flag${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⚠️  $key_name already exists at: $key_file${NC}"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Operation cancelled.${NC}"
            exit 0
        fi
    fi
}

# Generate Tenant RSA key pair (for Frontend ↔ Backend service authentication)
if [ "$GENERATE_TENANT" = true ]; then
    echo -e "${BLUE}🔐 Generating Tenant RSA key pair (service authentication)...${NC}"

    check_and_overwrite "$KEYS_DIR/tenant_private_key.pem" "Tenant private key"

    # Generate tenant private key
    echo -e "${BLUE}🔐 Generating tenant private key...${NC}"
    openssl genrsa -out "$KEYS_DIR/tenant_private_key.pem" 2048
    echo -e "${GREEN}✅ Tenant private key generated: $KEYS_DIR/tenant_private_key.pem${NC}"

    # Generate tenant public key
    echo -e "${BLUE}🔑 Generating tenant public key...${NC}"
    openssl rsa -in "$KEYS_DIR/tenant_private_key.pem" -pubout -out "$KEYS_DIR/tenant_public_key.pem"
    echo -e "${GREEN}✅ Tenant public key generated: $KEYS_DIR/tenant_public_key.pem${NC}"

    # Set proper permissions for tenant keys
    chmod 600 "$KEYS_DIR/tenant_private_key.pem"
    chmod 644 "$KEYS_DIR/tenant_public_key.pem"
    echo -e "${GREEN}✅ Tenant key permissions set${NC}"
fi

# Generate Frontend JWT key pair (for browser authentication)
if [ "$GENERATE_JWT" = true ]; then
    if [ "$GENERATE_TENANT" = true ]; then
        echo ""
    fi
    echo -e "${BLUE}🔐 Generating Frontend JWT key pair (browser authentication)...${NC}"

    check_and_overwrite "$KEYS_DIR/frontend_jwt_private_key.pem" "Frontend JWT private key"

    # Generate frontend JWT private key
    echo -e "${BLUE}🔐 Generating frontend JWT private key...${NC}"
    openssl genrsa -out "$KEYS_DIR/frontend_jwt_private_key.pem" 2048
    echo -e "${GREEN}✅ Frontend JWT private key generated: $KEYS_DIR/frontend_jwt_private_key.pem${NC}"

    # Generate frontend JWT public key
    echo -e "${BLUE}🔑 Generating frontend JWT public key...${NC}"
    openssl rsa -in "$KEYS_DIR/frontend_jwt_private_key.pem" -pubout -out "$KEYS_DIR/frontend_jwt_public_key.pem"
    echo -e "${GREEN}✅ Frontend JWT public key generated: $KEYS_DIR/frontend_jwt_public_key.pem${NC}"

    # Set proper permissions for JWT keys
    chmod 600 "$KEYS_DIR/frontend_jwt_private_key.pem"
    chmod 644 "$KEYS_DIR/frontend_jwt_public_key.pem"
    echo -e "${GREEN}✅ Frontend JWT key permissions set${NC}"
fi

# Display generated keys
echo ""
if [ "$GENERATE_TENANT" = true ]; then
    # Display tenant public key for backend registration
    echo -e "${BLUE}📋 Tenant public key content (for backend registration):${NC}"
    echo -e "${YELLOW}Copy this to register in the backend database:${NC}"
    echo "----------------------------------------"
    cat "$KEYS_DIR/tenant_public_key.pem"
    echo "----------------------------------------"
fi

if [ "$GENERATE_JWT" = true ]; then
    # Display frontend JWT public key
    if [ "$GENERATE_TENANT" = true ]; then
        echo ""
    fi
    echo -e "${BLUE}📋 Frontend JWT public key content:${NC}"
    echo -e "${YELLOW}This is for frontend JWT verification:${NC}"
    echo "----------------------------------------"
    cat "$KEYS_DIR/frontend_jwt_public_key.pem"
    echo "----------------------------------------"
fi

# Generate environment variables
echo -e "\n${BLUE}📝 Environment variables for .env.local:${NC}"
echo "----------------------------------------"
echo "# 注意：私钥通过 keyLoader 动态加载，不需要环境变量配置"
echo "# 注意：租户配置在前端代码中硬编码，私钥从文件系统加载"
echo "----------------------------------------"

echo -e "\n${GREEN}🎉 Key generation completed!${NC}"
echo -e "${YELLOW}Generated keys:${NC}"
if [ "$GENERATE_TENANT" = true ]; then
    echo "1. tenant_private_key.pem - Tenant RSA 私钥（服务间认证）"
    echo "2. tenant_public_key.pem - Tenant RSA 公钥（后端验证）"
fi
if [ "$GENERATE_JWT" = true ]; then
    echo "3. frontend_jwt_private_key.pem - Frontend JWT 私钥（浏览器认证）"
    echo "4. frontend_jwt_public_key.pem - Frontend JWT 公钥（浏览器验证）"
fi
echo -e "\n${YELLOW}Next steps:${NC}"
if [ "$GENERATE_TENANT" = true ]; then
    echo "1. Copy the tenant public key above to register in backend database"
fi
echo "2. Add environment variables to .env.local"
echo "3. Run: npm run generate-signature"
