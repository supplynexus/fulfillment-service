import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ScmOrderDetails } from '@/components/scm-orders/ScmOrderDetails';

export const metadata: Metadata = {
  title: 'SCM 订单详情 - SupplyNexus Fulfillment Service',
  description: '查看 SCM 订单的详细信息',
};

interface ScmOrderDetailsPageProps {
  params: {
    id: string;
  };
}

export default function ScmOrderDetailsPage({ params }: ScmOrderDetailsPageProps) {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ScmOrderDetails orderId={params.id} />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
