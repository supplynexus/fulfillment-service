#!/usr/bin/env python3
"""
Simple syntax checker for Python files
"""

import ast
import os
import sys
from pathlib import Path


def check_file_syntax(file_path: str) -> bool:
    """Check if a Python file has valid syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f"❌ Syntax Error in {file_path}:")
        print(f"   Line {e.lineno}: {e.text}")
        print(f"   Error: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False


def check_directory_syntax(directory: str) -> tuple[int, int]:
    """Check syntax for all Python files in a directory"""
    total_files = 0
    error_files = 0
    
    for root, dirs, files in os.walk(directory):
        # Skip virtual environment and cache directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                total_files += 1
                
                if not check_file_syntax(file_path):
                    error_files += 1
    
    return total_files, error_files


def main():
    """Main function"""
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "app"
    
    print(f"🔍 Checking syntax for Python files in: {target}")
    print("=" * 50)
    
    total_files, error_files = check_directory_syntax(target)
    
    print("=" * 50)
    print(f"📊 Summary:")
    print(f"   Total files checked: {total_files}")
    print(f"   Files with syntax errors: {error_files}")
    print(f"   Files with valid syntax: {total_files - error_files}")
    
    if error_files == 0:
        print("✅ All files have valid syntax!")
        return 0
    else:
        print("❌ Found syntax errors!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
