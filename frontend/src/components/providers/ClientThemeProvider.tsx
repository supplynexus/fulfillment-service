'use client';

import { ThemeProvider } from '@mui/material/styles';
import { Toaster } from 'react-hot-toast';

import { theme } from '@/lib/theme';

interface ClientThemeProviderProps {
  children: React.ReactNode;
}

export function ClientThemeProvider({ children }: ClientThemeProviderProps) {
  return (
    <ThemeProvider theme={theme}>
      {children}
      <Toaster
        position='top-right'
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            style: {
              background: '#4caf50',
            },
          },
          error: {
            duration: 5000,
            style: {
              background: '#f44336',
            },
          },
        }}
      />
    </ThemeProvider>
  );
}
