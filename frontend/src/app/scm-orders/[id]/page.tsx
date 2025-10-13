import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ScmOrderDetails } from '@/components/scm-orders/ScmOrderDetails';

export const metadata: Metadata = {
  title: 'SCM 订单详情 - SupplyNexus Fulfillment Service',
  description: '查看 SCM 订单的详细信息',
};

interface ScmOrderDetailsPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function ScmOrderDetailsPage({ params }: ScmOrderDetailsPageProps) {
  const { id } = await params;
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ScmOrderDetails orderId={id} />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
