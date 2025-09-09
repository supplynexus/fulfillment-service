import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductSync } from '@/components/products/ProductSync';

export const metadata: Metadata = {
  title: '商品同步 - SupplyNexus Fulfillment Service',
  description: '同步 Shopify 和 Printify 商品信息',
};

export default function ProductSyncPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ProductSync />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
