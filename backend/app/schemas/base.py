"""
通用Pydantic基类 - 解决审计字段类型问题

所有Response模型都应该继承这个基类，确保created_at和updated_at字段的类型一致性。
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class BaseResponse(BaseModel):
    """通用Response基类，包含审计字段"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BaseCreateRequest(BaseModel):
    """通用Create请求基类"""
    pass


class BaseUpdateRequest(BaseModel):
    """通用Update请求基类"""
    pass
