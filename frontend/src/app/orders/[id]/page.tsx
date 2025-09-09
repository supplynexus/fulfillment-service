import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { OrderDetails } from '@/components/orders/OrderDetails';

interface OrderDetailPageProps {
  params: Promise<{
    id: string;
  }>;
}

export async function generateMetadata({
  params,
}: OrderDetailPageProps): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `订单详情 #${id} - SupplyNexus Fulfillment Service`,
    description: `查看订单 #${id} 的详细信息和状态`,
  };
}

export default async function OrderDetailPage({
  params,
}: OrderDetailPageProps) {
  const { id } = await params;
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <OrderDetails orderId={id} />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
