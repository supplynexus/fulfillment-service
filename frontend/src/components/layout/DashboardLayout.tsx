'use client';

import { Box } from '@mui/material';
import { Header } from './Header';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Header />
      <Box component='main' sx={{ flexGrow: 1, bgcolor: 'grey.50' }}>
        {children}
      </Box>
    </Box>
  );
}
