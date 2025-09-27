import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { PlatformMapping } from '@/components/product-mapping/PlatformMapping';

export const metadata: Metadata = {
  title: 'Shopify 商品映射 - SupplyNexus Fulfillment Service',
  description: '管理核心商品与 Shopify 商品的映射关系',
};

export default function ShopifyMappingPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <PlatformMapping platform="shopify" />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
