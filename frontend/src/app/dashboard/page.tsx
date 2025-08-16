import { Metadata } from 'next';
import { Box, Container, Typography, Paper } from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

export const metadata: Metadata = {
  title: '仪表板 - SupplyNexus Fulfillment Service',
  description: 'SupplyNexus 履约服务管理系统仪表板',
};

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          仪表板
        </Typography>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' }, gap: 3, mb: 4 }}>
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              总订单数
            </Typography>
            <Typography variant="h4" color="primary">
              0
            </Typography>
          </Paper>
          
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              待处理订单
            </Typography>
            <Typography variant="h4" color="warning.main">
              0
            </Typography>
          </Paper>
          
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              已完成订单
            </Typography>
            <Typography variant="h4" color="success.main">
              0
            </Typography>
          </Paper>
          
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              产品数量
            </Typography>
            <Typography variant="h4" color="info.main">
              0
            </Typography>
          </Paper>
        </Box>
        
        <Box sx={{ mt: 4 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              欢迎使用 SupplyNexus 履约服务管理系统
            </Typography>
            <Typography variant="body1" color="text.secondary">
              这是一个现代化的订单履约管理系统，帮助您高效管理 Shopify 和 Printify 之间的订单流程。
            </Typography>
          </Paper>
        </Box>
        </Container>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
