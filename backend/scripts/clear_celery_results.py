"""
清理 Celery 结果后端中的旧任务结果
用于修复异常序列化问题
"""
import sys
import os

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import redis
from app.core.config import settings
import json

def clear_celery_results():
    """清理 Celery 结果后端中的所有任务结果"""
    try:
        # 连接到 Redis
        result_backend_url = settings.CELERY_RESULT_BACKEND
        print(f"📡 连接到 Redis: {result_backend_url}")
        
        # 解析 Redis URL
        if result_backend_url.startswith("redis://"):
            # 提取数据库编号
            if "/" in result_backend_url:
                db_num = int(result_backend_url.split("/")[-1])
            else:
                db_num = 0
            
            # 连接到 Redis
            client = redis.from_url(result_backend_url, decode_responses=False)
        else:
            print(f"❌ 不支持的 Redis URL 格式: {result_backend_url}")
            return
        
        # 获取所有 Celery 任务结果键
        pattern = "celery-task-meta-*"
        keys = client.keys(pattern)
        
        print(f"🔍 找到 {len(keys)} 个任务结果")
        
        if not keys:
            print("✅ 没有需要清理的任务结果")
            return
        
        # 删除所有失败的任务结果（更彻底的方法）
        deleted_count = 0
        for key in keys:
            try:
                # 检查结果格式
                value = client.get(key)
                if value:
                    try:
                        result_data = json.loads(value)
                        # 删除所有失败的任务结果，以及格式不正确的异常信息
                        if isinstance(result_data, dict):
                            status = result_data.get('status')
                            result = result_data.get('result')
                            
                            # 删除失败的任务
                            if status == 'FAILURE':
                                client.delete(key)
                                deleted_count += 1
                            # 删除格式不正确的异常信息
                            elif isinstance(result, dict) and 'exc_type' not in result and 'exc_message' in result:
                                print(f"⚠️  发现格式不正确的异常信息: {key.decode() if isinstance(key, bytes) else key}")
                                client.delete(key)
                                deleted_count += 1
                    except (json.JSONDecodeError, TypeError):
                        # 如果无法解析，也删除
                        print(f"⚠️  发现无法解析的结果: {key.decode() if isinstance(key, bytes) else key}")
                        client.delete(key)
                        deleted_count += 1
            except Exception as e:
                print(f"❌ 处理键 {key} 时出错: {e}")
        
        print(f"✅ 已清理 {deleted_count} 个任务结果")
        
        # 也可以选择清理所有结果（更彻底的方法）
        print("\n💡 提示: 如果需要清理所有任务结果，可以运行:")
        print("   python -c \"import redis; r=redis.from_url('YOUR_REDIS_URL'); r.flushdb()\"")
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    clear_celery_results()

