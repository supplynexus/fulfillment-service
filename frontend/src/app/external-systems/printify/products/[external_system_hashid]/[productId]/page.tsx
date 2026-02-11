'use client';

import React from 'react';
import { Box } from '@mui/material';
import { useParams } from 'next/navigation';

import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { PrintifyProductDetailView } from '@/components/printify/PrintifyProductDetailView';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

/**
 * Printify 商品详情页（路由呈现）。
 * 与列表弹窗共用同一控件 PrintifyProductDetailView，仅 variant=page，支持 URL 分享与刷新。
 */
function PrintifyProductDetailPage() {
  const params = useParams<{
    external_system_hashid: string;
    productId: string;
  }>();
  const externalSystemHashid = params?.external_system_hashid ?? null;
  const productId = params?.productId ?? null;

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box sx={{ p: 3 }}>
          <PrintifyProductDetailView
            variant='page'
            externalSystemHashid={
              typeof externalSystemHashid === 'string'
                ? externalSystemHashid
                : null
            }
            productId={
              typeof productId === 'string' ? productId : null
            }
            listPath='/external-systems/printify/products'
          />
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default PrintifyProductDetailPage;
