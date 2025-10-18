import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { ProductDetail } from '@/components/products/ProductDetail';

interface ProductDetailPageProps {
  params: Promise<{ product_hashid: string }>;
}

export async function generateMetadata({
  params,
}: ProductDetailPageProps): Promise<Metadata> {
  const { product_hashid } = await params;

  return {
    title: `商品详情 - ${product_hashid} - SupplyNexus Fulfillment Service`,
    description: '查看商品详细信息，包括变体、维度、标签和映射关系',
  };
}

export default async function ProductDetailPage({
  params,
}: ProductDetailPageProps) {
  const { product_hashid } = await params;

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <ProductDetail productHashId={product_hashid} />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
