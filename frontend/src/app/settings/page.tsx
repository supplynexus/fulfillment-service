import { Metadata } from 'next';
import { Container, Typography, Paper } from '@mui/material';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

export const metadata: Metadata = {
  title: '设置 - SupplyNexus Fulfillment Service',
  description: 'SupplyNexus 履约服务管理系统设置',
};

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <Container maxWidth='lg' sx={{ py: 4 }}>
          <Typography variant='h4' component='h1' gutterBottom>
            设置
          </Typography>

          <Paper sx={{ p: 3 }}>
            <Typography variant='h6' gutterBottom>
              系统设置
            </Typography>
            <Typography variant='body1' color='text.secondary'>
              设置页面正在开发中...
            </Typography>
          </Paper>
        </Container>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
