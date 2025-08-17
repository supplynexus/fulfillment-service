import { Metadata } from 'next';
import { Box, Container, Typography, Paper } from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

export const metadata: Metadata = {
  title: '个人资料 - SupplyNexus Fulfillment Service',
  description: 'SupplyNexus 履约服务管理系统个人资料',
};

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Container maxWidth='lg' sx={{ py: 4 }}>
          <Typography variant='h4' component='h1' gutterBottom>
            个人资料
          </Typography>

          <Paper sx={{ p: 3 }}>
            <Typography variant='h6' gutterBottom>
              用户信息
            </Typography>
            <Typography variant='body1' color='text.secondary'>
              个人资料页面正在开发中...
            </Typography>
          </Paper>
        </Container>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
