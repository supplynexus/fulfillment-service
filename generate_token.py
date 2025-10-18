#!/usr/bin/env python3
import jwt
from datetime import datetime, timedelta

# 使用后端的 SECRET_KEY
SECRET_KEY = "dev-secret-key-change-in-prod"
ALGORITHM = "HS256"

# 创建 payload
payload = {
    "sub": "2",  # user_id
    "tenant_id": 1,  # tenant_id
    "email": "frontend@supplynexus.store",
    "tenant_name": "impeach",
    "type": "access",
    "exp": datetime.utcnow() + timedelta(hours=1),  # 1小时后过期
    "iat": datetime.utcnow(),
}

# 生成 token
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(f"Generated JWT token: {token}")

# 验证 token
try:
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"Token decoded successfully: {decoded}")
except Exception as e:
    print(f"Token verification failed: {e}")
