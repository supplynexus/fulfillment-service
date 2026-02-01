import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductCreate } from '@/components/products/ProductCreate';

export const metadata: Metadata = {
  title: '创建商品 - SupplyNexus Fulfillment Service',
  description: '创建新商品，包括基本信息、变体、维度和标签',
};

export default function ProductCreatePage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ProductCreate />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
