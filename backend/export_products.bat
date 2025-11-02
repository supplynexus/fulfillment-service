@echo off
echo ========================================
echo 商品数据导出脚本
echo ========================================
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Python未安装或不在PATH中
    echo 请安装Python 3.7+并确保在PATH中
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
) else (
    echo 警告: 未找到虚拟环境，使用系统Python
    echo.
)

REM 检查requests模块是否存在
python -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo 检测到缺少 requests 模块，正在安装...
    python -m pip install requests
    if %errorlevel% neq 0 (
        echo 错误: 无法安装 requests 模块
        echo 请手动运行: pip install requests
        pause
        exit /b 1
    )
    echo ✅ requests 模块安装成功
    echo.
)

REM 检查配置文件是否存在
if not exist "product_export_config.json" (
    echo 错误: 配置文件不存在
    echo 请确保 product_export_config.json 文件存在
    pause
    exit /b 1
)

echo 开始导出商品数据...
echo.

REM 运行导出脚本
python export_products.py

echo.
echo 导出完成！
echo 生成的文件在 temp 目录中
echo.
pause


