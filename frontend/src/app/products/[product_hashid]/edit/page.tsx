import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductEdit } from '@/components/products/ProductEdit';

interface ProductEditPageProps {
  params: Promise<{ product_hashid: string }>;
}

export async function generateMetadata({ params }: ProductEditPageProps): Promise<Metadata> {
  const { product_hashid } = await params;
  
  return {
    title: `编辑商品 - ${product_hashid} - SupplyNexus Fulfillment Service`,
    description: '编辑商品信息，包括基本信息、变体、维度和标签',
  };
}

export default async function ProductEditPage({ params }: ProductEditPageProps) {
  const { product_hashid } = await params;

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ProductEdit productHashId={product_hashid} />
      </DashboardLayout>
    </ProtectedRoute>
  );
}