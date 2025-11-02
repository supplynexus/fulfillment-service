@echo off
echo ========================================
echo 安装导出脚本依赖
echo ========================================
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Python未安装或不在PATH中
    pause
    exit /b 1
)

REM 激活虚拟环境（如果存在）
if exist ".venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
)

echo 安装 requests 模块...
python -m pip install requests

if %errorlevel% equ 0 (
    echo.
    echo ✅ 依赖安装成功！
    echo.
) else (
    echo.
    echo ❌ 依赖安装失败，请检查网络连接和Python配置
    echo.
)

pause

