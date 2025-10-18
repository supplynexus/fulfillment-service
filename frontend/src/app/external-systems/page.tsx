'use client';

import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

function ExternalSystemsPage() {
  const router = useRouter();

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Box>
          <Typography variant="h4" gutterBottom>
            外部系统管理
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            管理和监控所有外部系统的连接状态和数据同步情况
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              onClick={() => router.push('/external-systems/shopify/stores')}
            >
              管理 Shopify
            </Button>
            <Button
              variant="contained"
              onClick={() => router.push('/external-systems/printify/stores')}
            >
              管理 Printify
            </Button>
          </Box>
        </Box>
      </DashboardLayout>
    </ProtectedRoute>
  );
}

export default ExternalSystemsPage;