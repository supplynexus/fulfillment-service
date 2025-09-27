import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { PlatformMapping } from '@/components/product-mapping/PlatformMapping';

export const metadata: Metadata = {
  title: 'Yahoo 商品映射 - SupplyNexus Fulfillment Service',
  description: '管理核心商品与 Yahoo 商品的映射关系',
};

export default function YahooMappingPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <PlatformMapping platform="yahoo" />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
