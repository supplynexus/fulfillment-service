"""
订单状态生命周期管理测试
测试订单从创建到完成的状态管理
"""

import pytest
from datetime import datetime
from app.services.order_lifecycle_service import OrderLifecycleService
from app.models.order import Order
from app.models.scm_order import SCMOrder


class TestOrderLifecycle:
    """订单状态生命周期测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.lifecycle_service = OrderLifecycleService()
    
    def test_order_status_transition_valid(self):
        """测试有效的订单状态转换"""
        # Red: 先写失败的测试
        valid_transitions = [
            ('created', 'processing'),
            ('processing', 'shipped'),
            ('shipped', 'delivered'),
            ('processing', 'cancelled'),
            ('shipped', 'returned')
        ]
        
        for from_status, to_status in valid_transitions:
            result = self.lifecycle_service.validate_status_transition(from_status, to_status)
            assert result is True, f"状态转换 {from_status} -> {to_status} 应该有效"
    
    def test_order_status_transition_invalid(self):
        """测试无效的订单状态转换"""
        # Red: 先写失败的测试
        invalid_transitions = [
            ('delivered', 'processing'),  # 已送达不能回到处理中
            ('cancelled', 'shipped'),     # 已取消不能变成已发货
            ('returned', 'processing'),   # 已退货不能回到处理中
            ('created', 'delivered')      # 创建不能直接到送达
        ]
        
        for from_status, to_status in invalid_transitions:
            result = self.lifecycle_service.validate_status_transition(from_status, to_status)
            assert result is False, f"状态转换 {from_status} -> {to_status} 应该无效"
    
    def test_order_status_lifecycle_complete(self):
        """测试完整的订单状态生命周期"""
        # Red: 先写失败的测试
        order_id = 1
        tenant_id = 1
        
        # 创建订单
        order = self.lifecycle_service.create_order(order_id, tenant_id)
        assert order.status == 'created'
        
        # 开始处理
        self.lifecycle_service.update_order_status(order_id, 'processing')
        assert order.status == 'processing'
        
        # 发货
        self.lifecycle_service.update_order_status(order_id, 'shipped')
        assert order.status == 'shipped'
        
        # 送达
        self.lifecycle_service.update_order_status(order_id, 'delivered')
        assert order.status == 'delivered'
    
    def test_order_status_validation_rules(self):
        """测试订单状态验证规则"""
        # Red: 先写失败的测试
        validation_rules = {
            'created': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'returned'],
            'delivered': ['returned'],
            'cancelled': [],
            'returned': []
        }
        
        for status, allowed_transitions in validation_rules.items():
            for target_status in ['created', 'processing', 'shipped', 'delivered', 'cancelled', 'returned']:
                if target_status in allowed_transitions:
                    result = self.lifecycle_service.validate_status_transition(status, target_status)
                    assert result is True, f"状态 {status} 应该能转换到 {target_status}"
                else:
                    result = self.lifecycle_service.validate_status_transition(status, target_status)
                    assert result is False, f"状态 {status} 不应该能转换到 {target_status}"
    
    def test_order_status_history_tracking(self):
        """测试订单状态历史记录"""
        # Red: 先写失败的测试
        order_id = 1
        tenant_id = 1
        
        # 创建订单
        order = self.lifecycle_service.create_order(order_id, tenant_id)
        
        # 更新状态
        self.lifecycle_service.update_order_status(order_id, 'processing')
        self.lifecycle_service.update_order_status(order_id, 'shipped')
        self.lifecycle_service.update_order_status(order_id, 'delivered')
        
        # 获取状态历史
        history = self.lifecycle_service.get_order_status_history(order_id)
        
        assert len(history) == 4  # created, processing, shipped, delivered
        assert history[0]['status'] == 'created'
        assert history[1]['status'] == 'processing'
        assert history[2]['status'] == 'shipped'
        assert history[3]['status'] == 'delivered'
    
    def test_order_status_exception_handling(self):
        """测试订单状态异常处理"""
        # Red: 先写失败的测试
        order_id = 999  # 不存在的订单
        
        # 尝试更新不存在的订单状态
        with pytest.raises(ValueError, match="订单不存在"):
            self.lifecycle_service.update_order_status(order_id, 'processing')
        
        # 尝试无效的状态转换
        with pytest.raises(ValueError, match="无效的状态转换"):
            self.lifecycle_service.update_order_status(1, 'invalid_status')
    
    def test_order_status_timestamp_tracking(self):
        """测试订单状态时间戳记录"""
        # Red: 先写失败的测试
        order_id = 1
        tenant_id = 1
        
        # 创建订单
        order = self.lifecycle_service.create_order(order_id, tenant_id)
        created_at = order.created_at
        
        # 更新状态
        self.lifecycle_service.update_order_status(order_id, 'processing')
        processing_at = datetime.utcnow()
        
        # 获取状态历史
        history = self.lifecycle_service.get_order_status_history(order_id)
        
        assert history[0]['timestamp'] == created_at
        assert history[1]['timestamp'] <= processing_at
        assert history[1]['timestamp'] >= created_at


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
