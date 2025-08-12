#!/bin/bash
# Generate RSA key pair for frontend authentication
# 为前端认证生成RSA密钥对

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Frontend Key Generator ===${NC}\n"

# Create keys directory if it doesn't exist
KEYS_DIR="$(dirname "$0")/../keys"
mkdir -p "$KEYS_DIR"

echo -e "${YELLOW}📁 Keys directory: $KEYS_DIR${NC}\n"

# Check if keys already exist
if [ -f "$KEYS_DIR/frontend_private_key.pem" ]; then
    echo -e "${YELLOW}⚠️  Private key already exists at: $KEYS_DIR/frontend_private_key.pem${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Operation cancelled.${NC}"
        exit 0
    fi
fi

# Generate private key
echo -e "${BLUE}🔐 Generating private key...${NC}"
openssl genrsa -out "$KEYS_DIR/frontend_private_key.pem" 2048
echo -e "${GREEN}✅ Private key generated: $KEYS_DIR/frontend_private_key.pem${NC}"

# Generate public key
echo -e "${BLUE}🔑 Generating public key...${NC}"
openssl rsa -in "$KEYS_DIR/frontend_private_key.pem" -pubout -out "$KEYS_DIR/frontend_public_key.pem"
echo -e "${GREEN}✅ Public key generated: $KEYS_DIR/frontend_public_key.pem${NC}"

# Set proper permissions
chmod 600 "$KEYS_DIR/frontend_private_key.pem"
chmod 644 "$KEYS_DIR/frontend_public_key.pem"
echo -e "${GREEN}✅ File permissions set${NC}"

# Display public key for registration
echo -e "\n${BLUE}📋 Public key content (for backend registration):${NC}"
echo -e "${YELLOW}Copy this to register in the backend database:${NC}"
echo "----------------------------------------"
cat "$KEYS_DIR/frontend_public_key.pem"
echo "----------------------------------------"

# Generate environment variables
echo -e "\n${BLUE}📝 Environment variables for .env.local:${NC}"
echo "----------------------------------------"
echo "FRONTEND_PRIVATE_KEY_PATH=$KEYS_DIR/frontend_private_key.pem"
echo "FRONTEND_KEY_ID=frontend-server-1"
echo "FRONTEND_USER_EMAIL=frontend@supplynexus.store"
echo "NEXT_PUBLIC_TENANT_HASHID=PoRpOk2e"
echo "----------------------------------------"

echo -e "\n${GREEN}🎉 Key generation completed!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy the public key above to register in backend database"
echo "2. Add environment variables to .env.local"
echo "3. Run: npm run generate-signature"
