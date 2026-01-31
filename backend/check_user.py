#!/usr/bin/env python3
import asyncio
from sqlalchemy import create_engine, text
from app.core.config import settings

def check_user():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, email, hashed_password FROM users WHERE email = 'admin'"))
        user = result.fetchone()
        if user:
            print(f'User ID: {user[0]}')
            print(f'Email: {user[1]}')
            print(f'Password Hash: {user[2]}')
            
            # 测试密码验证
            from app.core.auth import verify_password
            test_password = "admin123"
            is_valid = verify_password(test_password, user[2])
            print(f'Password verification result: {is_valid}')
        else:
            print('User not found')

if __name__ == "__main__":
    check_user()
