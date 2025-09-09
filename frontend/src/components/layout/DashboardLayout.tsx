'use client';

import { useState } from 'react';
import { Box } from '@mui/material';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleSidebarToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar open={sidebarOpen} onToggle={handleSidebarToggle} />
      <Box sx={{ display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
        <Header />
        <Box
          component='main'
          sx={{
            flexGrow: 1,
            bgcolor: 'grey.50',
            p: 3,
            transition: 'margin-left 0.3s ease',
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
