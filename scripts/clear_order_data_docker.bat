@echo off
REM 清理订单数据脚本 (Docker版本 - Windows)
REM 用于清空所有订单相关数据，重新测试订单自动化流程

echo 🧹 订单数据清理工具 (Docker版本)
echo ==================================================

REM 检查Docker是否运行
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker未运行，请先启动Docker Desktop
    exit /b 1
)

REM 检查docker-compose文件是否存在
if not exist "docker-compose.yml" (
    echo ❌ docker-compose.yml文件不存在
    exit /b 1
)

echo ⚠️ 此操作将删除所有订单数据
set /p confirm="是否继续？(y/N): "

if not "%confirm%"=="y" if not "%confirm%"=="Y" (
    echo ❌ 操作已取消
    exit /b 0
)

echo 🔍 开始清理订单数据...

REM 在Docker容器中执行清理脚本
docker-compose exec backend python -c "
import sys
sys.path.append('/app')
from sqlalchemy import text
from app.core.database import get_sync_db
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    logger.info('🧹 开始清理订单数据...')
    
    # 获取数据库连接
    db = next(get_sync_db())
    
    # 清理顺序：先清理依赖表，再清理主表
    tables_to_clear = [
        'routing_status',      # 路由状态表
        'scm_orders',          # SCM订单表
        'orders',              # 订单表
    ]
    
    for table in tables_to_clear:
        try:
            # 检查表是否存在
            result = db.execute(text(f'''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
            '''))
            
            table_exists = result.scalar()
            
            if table_exists:
                # 清空表数据
                db.execute(text(f'DELETE FROM {table};'))
                logger.info(f'✅ 已清空表: {table}')
                print(f'✅ 已清空表: {table}')
            else:
                logger.warning(f'⚠️ 表不存在: {table}')
                print(f'⚠️ 表不存在: {table}')
                
        except Exception as e:
            logger.error(f'❌ 清空表 {table} 失败: {str(e)}')
            print(f'❌ 清空表 {table} 失败: {str(e)}')
            continue
    
    # 重置自增ID序列
    try:
        # 重置orders表的ID序列
        db.execute(text('SELECT setval(\"orders_id_seq\", 1, false);'))
        logger.info('✅ 已重置 orders 表ID序列')
        print('✅ 已重置 orders 表ID序列')
    except Exception as e:
        logger.warning(f'⚠️ 重置 orders 表ID序列失败: {str(e)}')
        print(f'⚠️ 重置 orders 表ID序列失败: {str(e)}')
    
    try:
        # 重置scm_orders表的ID序列
        db.execute(text('SELECT setval(\"scm_orders_id_seq\", 1, false);'))
        logger.info('✅ 已重置 scm_orders 表ID序列')
        print('✅ 已重置 scm_orders 表ID序列')
    except Exception as e:
        logger.warning(f'⚠️ 重置 scm_orders 表ID序列失败: {str(e)}')
        print(f'⚠️ 重置 scm_orders 表ID序列失败: {str(e)}')
    
    try:
        # 重置routing_status表的ID序列
        db.execute(text('SELECT setval(\"routing_status_id_seq\", 1, false);'))
        logger.info('✅ 已重置 routing_status 表ID序列')
        print('✅ 已重置 routing_status 表ID序列')
    except Exception as e:
        logger.warning(f'⚠️ 重置 routing_status 表ID序列失败: {str(e)}')
        print(f'⚠️ 重置 routing_status 表ID序列失败: {str(e)}')
    
    # 提交事务
    db.commit()
    
    logger.info('🎉 订单数据清理完成！')
    print('🎉 订单数据清理完成！')
    
    # 验证清理结果
    print('🔍 验证清理结果...')
    tables_to_check = ['orders', 'scm_orders', 'routing_status']
    
    for table in tables_to_check:
        try:
            result = db.execute(text(f'SELECT COUNT(*) FROM {table};'))
            count = result.scalar()
            logger.info(f'{table} 表记录数: {count}')
            print(f'📊 {table} 表记录数: {count}')
        except Exception as e:
            logger.warning(f'检查表 {table} 失败: {str(e)}')
            print(f'⚠️ 检查表 {table} 失败: {str(e)}')
    
    db.close()
    
except Exception as e:
    logger.error(f'❌ 清理订单数据失败: {str(e)}')
    print(f'❌ 清理订单数据失败: {str(e)}')
    if 'db' in locals():
        db.rollback()
    sys.exit(1)
"

if %errorlevel% equ 0 (
    echo.
    echo ✅ 订单数据清理完成！
    echo 🚀 现在可以重新测试订单自动化流程了
    echo.
    echo 📋 可用的测试步骤：
    echo 1. 确保Shopify和Printify外部系统已配置
    echo 2. 同步Shopify订单到本地
    echo 3. 触发订单自动化流程
    echo 4. 检查SCM订单创建和Printify订单生成
    echo 5. 验证状态同步和Shopify履约更新
) else (
    echo.
    echo ❌ 订单数据清理失败！
    exit /b 1
)
