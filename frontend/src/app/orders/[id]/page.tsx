import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { OrderDetails } from '@/components/orders/OrderDetails';

interface OrderDetailPageProps {
  params: {
    id: string;
  };
}

export async function generateMetadata({ params }: OrderDetailPageProps): Promise<Metadata> {
  return {
    title: `订单详情 #${params.id} - SupplyNexus Fulfillment Service`,
    description: `查看订单 #${params.id} 的详细信息和状态`,
  };
}

export default function OrderDetailPage({ params }: OrderDetailPageProps) {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <OrderDetails orderId={params.id} />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
