import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductMappingOverview } from '@/components/product-mapping/ProductMappingOverview';

export const metadata: Metadata = {
  title: '商品映射总览 - SupplyNexus Fulfillment Service',
  description: '管理核心商品与外部平台商品的映射关系',
};

export default function ProductMappingPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ProductMappingOverview />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
