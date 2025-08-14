#!/usr/bin/env python3
"""
依赖检查工具
验证Python 3.12环境下的所有依赖是否正确安装
"""

import sys
import importlib
import logging
from typing import List, Tuple

# 添加项目根目录到Python路径
sys.path.append('.')

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_python_version():
    """检查Python版本"""
    logger.info("🔍 检查Python版本...")
    
    version = sys.version_info
    logger.info(f"   当前Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 12:
        logger.info("✅ Python版本符合要求 (3.12+)")
        return True
    else:
        logger.error(f"❌ Python版本不符合要求，需要3.12+，当前为{version.major}.{version.minor}")
        return False


def check_dependency(module_name: str, package_name: str = None) -> Tuple[bool, str]:
    """
    检查单个依赖模块
    
    Args:
        module_name: 模块名称
        package_name: 包名称（如果与模块名称不同）
    
    Returns:
        (是否成功, 错误信息)
    """
    try:
        importlib.import_module(module_name)
        return True, ""
    except ImportError as e:
        error_msg = f"无法导入 {module_name}: {e}"
        if package_name and package_name != module_name:
            error_msg += f" (请安装: pip install {package_name})"
        return False, error_msg


def check_core_dependencies() -> List[Tuple[str, bool, str]]:
    """检查核心依赖"""
    logger.info("🔍 检查核心依赖...")
    
    core_deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn[standard]"),
        ("sqlalchemy", "sqlalchemy"),
        ("alembic", "alembic"),
        ("asyncpg", "asyncpg"),
        ("psycopg2", "psycopg2-binary"),
        ("greenlet", "greenlet"),
        ("redis", "redis"),
        ("celery", "celery"),
        ("jose", "python-jose[cryptography]"),
        ("passlib", "passlib[bcrypt]"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        ("aiohttp", "aiohttp"),
        ("httpx", "httpx"),
        ("cryptography", "cryptography"),
        ("dotenv", "python-dotenv"),
        ("structlog", "structlog"),
        ("sentry_sdk", "sentry-sdk[fastapi]"),
    ]
    
    results = []
    for module_name, package_name in core_deps:
        success, error = check_dependency(module_name, package_name)
        results.append((module_name, success, error))
        
        if success:
            logger.info(f"✅ {module_name}")
        else:
            logger.error(f"❌ {module_name}: {error}")
    
    return results


def check_dev_dependencies() -> List[Tuple[str, bool, str]]:
    """检查开发依赖"""
    logger.info("🔍 检查开发依赖...")
    
    dev_deps = [
        ("pytest", "pytest"),
        ("pytest_asyncio", "pytest-asyncio"),
        ("pytest_cov", "pytest-cov"),
        ("factory_boy", "factory-boy"),
        ("black", "black"),
        ("isort", "isort"),
        ("flake8", "flake8"),
        ("mypy", "mypy"),
        ("pre_commit", "pre-commit"),
    ]
    
    results = []
    for module_name, package_name in dev_deps:
        success, error = check_dependency(module_name, package_name)
        results.append((module_name, success, error))
        
        if success:
            logger.info(f"✅ {module_name}")
        else:
            logger.warning(f"⚠️  {module_name}: {error} (开发依赖，可选)")
    
    return results


def check_optional_dependencies() -> List[Tuple[str, bool, str]]:
    """检查可选依赖"""
    logger.info("🔍 检查可选依赖...")
    
    optional_deps = [
        ("sphinx", "sphinx"),
        ("sphinx_autodoc_typehints", "sphinx-autodoc-typehints"),
        ("flower", "flower"),
        ("ShopifyAPI", "ShopifyAPI"),
    ]
    
    results = []
    for module_name, package_name in optional_deps:
        success, error = check_dependency(module_name, package_name)
        results.append((module_name, success, error))
        
        if success:
            logger.info(f"✅ {module_name}")
        else:
            logger.info(f"ℹ️  {module_name}: {error} (可选依赖)")
    
    return results


def check_app_modules():
    """检查应用模块"""
    logger.info("🔍 检查应用模块...")
    
    app_modules = [
        "app.core.config",
        "app.core.database",
        "app.core.auth",
        "app.models.order",
        "app.models.product",
        "app.services.shopify.client",
        "app.tasks.celery_app",
    ]
    
    results = []
    for module_name in app_modules:
        success, error = check_dependency(module_name)
        results.append((module_name, success, error))
        
        if success:
            logger.info(f"✅ {module_name}")
        else:
            logger.error(f"❌ {module_name}: {error}")
    
    return results


def generate_install_commands(failed_deps: List[Tuple[str, str]]) -> str:
    """生成安装命令"""
    if not failed_deps:
        return "所有依赖都已正确安装！"
    
    commands = []
    for module_name, package_name in failed_deps:
        if package_name:
            commands.append(f"pip3.12 install {package_name}")
    
    if commands:
        return "\n".join(commands)
    else:
        return "请手动安装缺失的依赖"


def main():
    """主函数"""
    logger.info("🚀 开始依赖检查")
    logger.info("=" * 50)
    
    # 检查Python版本
    python_ok = check_python_version()
    if not python_ok:
        logger.error("❌ Python版本检查失败，请升级到Python 3.12+")
        sys.exit(1)
    
    logger.info("")
    
    # 检查各种依赖
    core_results = check_core_dependencies()
    logger.info("")
    
    dev_results = check_dev_dependencies()
    logger.info("")
    
    optional_results = check_optional_dependencies()
    logger.info("")
    
    app_results = check_app_modules()
    logger.info("")
    
    # 统计结果
    core_failed = [(name, "") for name, success, _ in core_results if not success]
    dev_failed = [(name, "") for name, success, _ in dev_results if not success]
    optional_failed = [(name, "") for name, success, _ in optional_results if not success]
    app_failed = [(name, "") for name, success, _ in app_results if not success]
    
    total_core = len(core_results)
    total_dev = len(dev_results)
    total_optional = len(optional_results)
    total_app = len(app_results)
    
    passed_core = total_core - len(core_failed)
    passed_dev = total_dev - len(dev_failed)
    passed_optional = total_optional - len(optional_failed)
    passed_app = total_app - len(app_failed)
    
    # 输出统计
    logger.info("🎯 依赖检查结果汇总")
    logger.info("=" * 50)
    logger.info(f"   核心依赖: {passed_core}/{total_core} 通过")
    logger.info(f"   开发依赖: {passed_dev}/{total_dev} 通过")
    logger.info(f"   可选依赖: {passed_optional}/{total_optional} 通过")
    logger.info(f"   应用模块: {passed_app}/{total_app} 通过")
    
    if core_failed:
        logger.error(f"❌ 核心依赖缺失 ({len(core_failed)} 个):")
        for name, _ in core_failed:
            logger.error(f"   - {name}")
    
    if app_failed:
        logger.error(f"❌ 应用模块缺失 ({len(app_failed)} 个):")
        for name, _ in app_failed:
            logger.error(f"   - {name}")
    
    if dev_failed:
        logger.warning(f"⚠️  开发依赖缺失 ({len(dev_failed)} 个):")
        for name, _ in dev_failed:
            logger.warning(f"   - {name}")
    
    # 生成安装建议
    if core_failed or app_failed:
        logger.info("")
        logger.info("🔧 安装建议:")
        logger.info("=" * 30)
        
        # 收集所有失败的包名
        failed_packages = []
        for name, success, error in core_results + app_results:
            if not success:
                # 从错误信息中提取包名
                if "pip install" in error:
                    package_name = error.split("pip install ")[-1].split(")")[0]
                    failed_packages.append(package_name)
                else:
                    failed_packages.append(name)
        
        if failed_packages:
            logger.info("请运行以下命令安装缺失的依赖:")
            for package in set(failed_packages):
                logger.info(f"   pip3.12 install {package}")
        
        logger.info("")
        logger.info("或者运行:")
        logger.info("   pip3.12 install -r requirements.txt")
    
    # 最终结果
    if not core_failed and not app_failed:
        logger.info("✅ 所有必需的依赖都已正确安装！")
        return True
    else:
        logger.error("❌ 存在缺失的必需依赖，请安装后重试")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("检查被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"检查过程中出现未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
