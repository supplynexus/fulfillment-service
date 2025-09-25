import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ScmOrdersList } from '@/components/scm-orders/ScmOrdersList';

export const metadata: Metadata = {
  title: 'SCM 订单管理 - SupplyNexus Fulfillment Service',
  description: '管理 SCM 订单，查看订单路由和履行状态',
};

export default function ScmOrdersPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ScmOrdersList />
      </DashboardLayout>
    </ProtectedRoute>
  );
}