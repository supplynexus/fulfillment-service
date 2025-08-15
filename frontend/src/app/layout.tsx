import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { Toaster } from 'react-hot-toast';

import { theme } from '@/lib/theme';
import { QueryProvider } from '@/lib/query-client';
import { AuthProvider } from '@/lib/auth-context';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'SupplyNexus Fulfillment Service',
  description: 'Shopify to Printify Order Fulfillment Automation Dashboard',
  keywords: ['fulfillment', 'shopify', 'printify', 'automation', 'ecommerce'],
  authors: [{ name: 'SupplyNexus' }],
  viewport: 'width=device-width, initial-scale=1',
  robots: 'noindex, nofollow', // Private admin dashboard
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang='en'>
      <body className={inter.className}>
        <AppRouterCacheProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <QueryProvider>
              <AuthProvider>
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
              </AuthProvider>
            </QueryProvider>
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
