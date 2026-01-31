"""
地址验证服务
用于验证订单收货地址的有效性
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AddressValidationResult:
    """地址验证结果"""
    status: str  # 'valid', 'invalid', 'suspicious', 'failed', 'not_checked'
    reason_code: Optional[str] = None
    message: Optional[str] = None
    validated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.validated_at is None:
            self.validated_at = datetime.now(timezone.utc)


def validate_address(address: Dict[str, Any]) -> AddressValidationResult:
    """
    验证地址的有效性
    
    Args:
        address: 地址字典，包含以下字段：
            - address1: 街道地址1
            - city: 城市
            - province: 省/州
            - country: 国家
            - zip: 邮编
    
    Returns:
        AddressValidationResult: 验证结果
    """
    try:
        if not address:
            return AddressValidationResult(
                status="invalid",
                reason_code="MISSING_ADDRESS",
                message="地址信息为空"
            )
        
        # 提取地址字段
        address1 = address.get("address1", "").strip()
        city = address.get("city", "").strip()
        province = address.get("province", "").strip()
        country = address.get("country", "").strip()
        zip_code = address.get("zip", "").strip()
        
        # 基础验证规则
        issues = []
        
        # 检查必填字段
        if not address1:
            issues.append("缺少街道地址")
        
        if not city:
            issues.append("缺少城市信息")
        
        if not country:
            issues.append("缺少国家信息")
        
        # 检查地址格式
        if address1 and len(address1) < 5:
            issues.append("街道地址过短，可能不完整")
        
        if zip_code:
            # 基本邮编格式检查（至少3个字符）
            if len(zip_code) < 3:
                issues.append("邮编格式可能不正确")
        else:
            # 某些国家邮编是可选的，但大多数国家需要
            # 这里只作为警告，不标记为错误
            pass
        
        # 检查可疑地址模式
        suspicious_patterns = [
            "test", "example", "sample", "demo", "fake",
            "123 test", "test street", "test address"
        ]
        address_lower = address1.lower()
        if any(pattern in address_lower for pattern in suspicious_patterns):
            issues.append("地址包含测试关键词")
        
        # 根据问题数量确定状态
        if len(issues) == 0:
            return AddressValidationResult(
                status="valid",
                reason_code="VALID",
                message="地址通过基础验证"
            )
        elif len(issues) == 1 and "邮编" in issues[0]:
            # 只有邮编问题，标记为可疑但不阻止
            return AddressValidationResult(
                status="suspicious",
                reason_code="MISSING_OR_INVALID_ZIP",
                message="; ".join(issues)
            )
        elif len(issues) <= 2:
            # 少量问题，标记为可疑
            return AddressValidationResult(
                status="suspicious",
                reason_code="ADDRESS_INCOMPLETE",
                message="; ".join(issues)
            )
        else:
            # 多个问题，标记为无效
            return AddressValidationResult(
                status="invalid",
                reason_code="ADDRESS_INVALID",
                message="; ".join(issues)
            )
    
    except Exception as e:
        logger.error(f"地址验证过程中发生异常: {e}")
        return AddressValidationResult(
            status="failed",
            reason_code="VALIDATION_EXCEPTION",
            message=f"验证过程出错: {str(e)}"
        )
