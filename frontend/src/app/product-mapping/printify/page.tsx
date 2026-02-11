import { Metadata } from 'next';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { PrintifyMapping } from '@/components/product-mapping/PrintifyMapping';

export const metadata: Metadata = {
  title: 'Printify 商品映射 - SupplyNexus Fulfillment Service',
  description: '管理核心商品与 Printify 商品的映射关系',
};

type PageProps = {
  searchParams: Promise<{ core_product_id?: string; printify_product_id?: string }>;
};

export default async function PrintifyMappingPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const initialCoreProductIdHashid = params?.core_product_id?.trim() || undefined;
  const initialPrintifyProductId = params?.printify_product_id?.trim() || undefined;
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <PrintifyMapping
          initialCoreProductIdHashid={initialCoreProductIdHashid}
          initialPrintifyProductId={initialPrintifyProductId}
        />
      </DashboardLayout>
    </ProtectedRoute>
  );
}
