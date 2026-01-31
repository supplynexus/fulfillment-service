import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { OrdersList } from '@/components/orders/OrdersList';

export const metadata: Metadata = {
  title: '订单管理 - SupplyNexus Fulfillment Service',
  description: '管理所有订单，查看订单状态和详情',
};

export default function OrdersPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <OrdersList />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
