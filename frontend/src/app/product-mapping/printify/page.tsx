import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { PrintifyMapping } from '@/components/product-mapping/PrintifyMapping';

export const metadata: Metadata = {
  title: 'Printify 商品映射 - SupplyNexus Fulfillment Service',
  description: '管理核心商品与 Printify 商品的映射关系',
};

export default function PrintifyMappingPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <PrintifyMapping />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
