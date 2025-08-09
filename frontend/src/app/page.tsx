'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Container, Box, CircularProgress, Typography } from '@mui/material';

import { useAuth } from '@/lib/auth-context';

export default function HomePage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (user) {
        router.push('/dashboard');
      } else {
        router.push('/auth/login');
      }
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <Container maxWidth='sm'>
        <Box
          display='flex'
          flexDirection='column'
          alignItems='center'
          justifyContent='center'
          minHeight='100vh'
          gap={2}
        >
          <CircularProgress size={48} />
          <Typography variant='h6' color='textSecondary'>
            Loading SupplyNexus Fulfillment Service...
          </Typography>
        </Box>
      </Container>
    );
  }

  return null;
}
