#!/usr/bin/env python3
"""
User Management Tool

This tool allows administrators to manage users in the database.
It provides secure password hashing and user creation/update functionality.

Usage:
    python scripts/user_manager.py create <email> <password> [--full-name <name>]
    python scripts/user_manager.py update <email> <new_password>
    python scripts/user_manager.py list
    python scripts/user_manager.py show <email>
    python scripts/user_manager.py delete <email>
"""

import asyncio
import argparse
import sys
import os
from typing import Optional

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.auth import hash_password, verify_password, is_password_strong
from app.models.user import User
from app.services.user_service import UserService


class UserManager:
    def __init__(self):
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def create_user(self, email: str, password: str, full_name: Optional[str] = None) -> bool:
        """
        Create a new user with secure password hashing
        
        Args:
            email: User's email address
            password: Plain text password
            full_name: Optional full name
            
        Returns:
            bool: True if successful, False otherwise
        """
        async with self.async_session() as db:
            try:
                # Check if user already exists
                existing_user = await db.execute(
                    select(User).where(User.email == email)
                )
                if existing_user.scalar_one_or_none():
                    print(f"❌ User with email '{email}' already exists")
                    return False

                # Validate password strength
                is_strong, message = is_password_strong(password)
                if not is_strong:
                    print(f"❌ Password validation failed: {message}")
                    return False

                # Create user service and user
                user_service = UserService(db)
                user, message = await user_service.create({
                    "email": email,
                    "password": password,
                    "full_name": full_name,
                    "is_active": True,
                    "is_superuser": False
                })

                if user:
                    print(f"✅ User '{email}' created successfully")
                    print(f"   Full Name: {full_name or 'Not set'}")
                    print(f"   User ID: {user.id}")
                    print(f"   Password: {message}")
                    return True
                else:
                    print(f"❌ Failed to create user: {message}")
                    return False

            except Exception as e:
                print(f"❌ Error creating user: {str(e)}")
                return False

    async def update_password(self, email: str, new_password: str) -> bool:
        """
        Update user's password with secure hashing
        
        Args:
            email: User's email address
            new_password: New plain text password
            
        Returns:
            bool: True if successful, False otherwise
        """
        async with self.async_session() as db:
            try:
                # Find user
                user = await db.execute(
                    select(User).where(User.email == email)
                )
                user = user.scalar_one_or_none()
                
                if not user:
                    print(f"❌ User with email '{email}' not found")
                    return False

                # Validate password strength
                is_strong, message = is_password_strong(new_password)
                if not is_strong:
                    print(f"❌ Password validation failed: {message}")
                    return False

                # Update password
                success, message = user.set_password(new_password)
                if success:
                    await db.commit()
                    print(f"✅ Password updated successfully for user '{email}'")
                    print(f"   Password: {message}")
                    return True
                else:
                    print(f"❌ Failed to update password: {message}")
                    return False

            except Exception as e:
                print(f"❌ Error updating password: {str(e)}")
                return False

    async def list_users(self) -> bool:
        """
        List all users in the database
        
        Returns:
            bool: True if successful, False otherwise
        """
        async with self.async_session() as db:
            try:
                users = await db.execute(select(User))
                users = users.scalars().all()
                
                if not users:
                    print("📋 No users found in database")
                    return True

                print(f"📋 Found {len(users)} user(s):")
                print("-" * 80)
                print(f"{'ID':<5} {'Email':<30} {'Full Name':<20} {'Active':<8} {'Superuser':<10}")
                print("-" * 80)
                
                for user in users:
                    print(f"{user.id:<5} {user.email:<30} {(user.full_name or 'N/A')[:19]:<20} {str(user.is_active):<8} {str(user.is_superuser):<10}")
                
                return True

            except Exception as e:
                print(f"❌ Error listing users: {str(e)}")
                return False

    async def show_user(self, email: str) -> bool:
        """
        Show detailed information about a specific user
        
        Args:
            email: User's email address
            
        Returns:
            bool: True if successful, False otherwise
        """
        async with self.async_session() as db:
            try:
                user = await db.execute(
                    select(User).where(User.email == email)
                )
                user = user.scalar_one_or_none()
                
                if not user:
                    print(f"❌ User with email '{email}' not found")
                    return False

                print(f"👤 User Details for '{email}':")
                print("-" * 50)
                print(f"ID: {user.id}")
                print(f"Email: {user.email}")
                print(f"Full Name: {user.full_name or 'Not set'}")
                print(f"Active: {user.is_active}")
                print(f"Superuser: {user.is_superuser}")
                print(f"Created: {user.created_at}")
                print(f"Updated: {user.updated_at}")
                print(f"Password Changed: {user.password_changed_at or 'Never'}")
                print(f"Last Login: {user.last_login_at or 'Never'}")
                print(f"Failed Login Attempts: {user.failed_login_attempts}")
                print(f"Locked Until: {user.locked_until or 'Not locked'}")
                print(f"Password Expires: {user.password_expires_at or 'Never'}")
                
                return True

            except Exception as e:
                print(f"❌ Error showing user: {str(e)}")
                return False

    async def delete_user(self, email: str) -> bool:
        """
        Delete a user from the database
        
        Args:
            email: User's email address
            
        Returns:
            bool: True if successful, False otherwise
        """
        async with self.async_session() as db:
            try:
                user = await db.execute(
                    select(User).where(User.email == email)
                )
                user = user.scalar_one_or_none()
                
                if not user:
                    print(f"❌ User with email '{email}' not found")
                    return False

                # Confirm deletion
                confirm = input(f"⚠️  Are you sure you want to delete user '{email}'? (yes/no): ")
                if confirm.lower() != 'yes':
                    print("❌ User deletion cancelled")
                    return False

                await db.delete(user)
                await db.commit()
                print(f"✅ User '{email}' deleted successfully")
                return True

            except Exception as e:
                print(f"❌ Error deleting user: {str(e)}")
                return False

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()


async def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(
        description="User Management Tool for SupplyNexus Fulfillment Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/user_manager.py create admin@example.com MySecurePass123! --full-name "Admin User"
  python scripts/user_manager.py update admin@example.com NewSecurePass123!
  python scripts/user_manager.py list
  python scripts/user_manager.py show admin@example.com
  python scripts/user_manager.py delete admin@example.com
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create user command
    create_parser = subparsers.add_parser('create', help='Create a new user')
    create_parser.add_argument('email', help='User email address')
    create_parser.add_argument('password', help='User password')
    create_parser.add_argument('--full-name', help='User full name')
    
    # Update password command
    update_parser = subparsers.add_parser('update', help='Update user password')
    update_parser.add_argument('email', help='User email address')
    update_parser.add_argument('password', help='New password')
    
    # List users command
    subparsers.add_parser('list', help='List all users')
    
    # Show user command
    show_parser = subparsers.add_parser('show', help='Show user details')
    show_parser.add_argument('email', help='User email address')
    
    # Delete user command
    delete_parser = subparsers.add_parser('delete', help='Delete a user')
    delete_parser.add_argument('email', help='User email address')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create user manager
    user_manager = UserManager()
    
    try:
        if args.command == 'create':
            success = await user_manager.create_user(args.email, args.password, args.full_name)
        elif args.command == 'update':
            success = await user_manager.update_password(args.email, args.password)
        elif args.command == 'list':
            success = await user_manager.list_users()
        elif args.command == 'show':
            success = await user_manager.show_user(args.email)
        elif args.command == 'delete':
            success = await user_manager.delete_user(args.email)
        else:
            print(f"❌ Unknown command: {args.command}")
            success = False
        
        if success:
            print("✅ Operation completed successfully")
        else:
            print("❌ Operation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        await user_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
