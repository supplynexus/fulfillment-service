#!/usr/bin/env python3
"""
快速检查脚本 - 在启动前检查基本语法和导入
"""

import sys
import subprocess
from pathlib import Path


def check_syntax():
    """检查Python语法"""
    print("🔍 检查Python语法...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "py_compile", "app/main.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 语法检查通过")
            return True
        else:
            print(f"❌ 语法错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 语法检查失败: {e}")
        return False


def check_imports():
    """检查导入"""
    print("🔍 检查导入...")
    
    try:
        result = subprocess.run([
            sys.executable, "-c", "import app.main"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 导入检查通过")
            return True
        else:
            print(f"❌ 导入错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 导入检查失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 快速检查开始...")
    
    # 检查语法
    syntax_ok = check_syntax()
    
    # 检查导入
    imports_ok = check_imports()
    
    if syntax_ok and imports_ok:
        print("🎉 所有检查通过！可以启动后端服务")
        sys.exit(0)
    else:
        print("❌ 检查失败，请修复错误后再启动")
        sys.exit(1)


if __name__ == "__main__":
    main()
