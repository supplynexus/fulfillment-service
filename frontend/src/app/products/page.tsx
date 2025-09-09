import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductsList } from '@/components/products/ProductsList';

export const metadata: Metadata = {
  title: '商品管理 - SupplyNexus Fulfillment Service',
  description: '管理商品信息，查看商品同步状态',
};

export default function ProductsPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ProductsList />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
