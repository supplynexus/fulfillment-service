import { Metadata } from 'next';
import { Box, Container, Typography } from '@mui/material';
import { LoginForm } from '@/components/auth/LoginForm';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

export const metadata: Metadata = {
  title: '登录 - SupplyNexus Fulfillment Service',
  description: '登录到 SupplyNexus 履约服务管理系统',
};

export default function LoginPage() {
  return (
    <ProtectedRoute requireAuth={false}>
      <Container maxWidth="sm">
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            mb: 4,
          }}
        >
          <Typography
            variant="h3"
            component="h1"
            sx={{
              fontWeight: 700,
              color: 'white',
              mb: 1,
              textShadow: '0 2px 4px rgba(0,0,0,0.3)',
            }}
          >
            SupplyNexus
          </Typography>
          <Typography
            variant="h6"
            sx={{
              color: 'rgba(255,255,255,0.9)',
              fontWeight: 400,
              textShadow: '0 1px 2px rgba(0,0,0,0.3)',
            }}
          >
            履约服务管理系统
          </Typography>
        </Box>
        <LoginForm />
      </Container>
    </ProtectedRoute>
  );
}
