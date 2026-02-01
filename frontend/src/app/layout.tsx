import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import CssBaseline from '@mui/material/CssBaseline';
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';

import { ClientThemeProvider } from '@/components/providers/ClientThemeProvider';
import { QueryProvider } from '@/lib/query-client';
import { AuthProvider } from '@/lib/auth-context';
import { EnvironmentBadge } from '@/components/EnvironmentBadge';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'SupplyNexus Fulfillment Service',
  description: 'Shopify to Printify Order Fulfillment Automation Dashboard',
  keywords: ['fulfillment', 'shopify', 'printify', 'automation', 'ecommerce'],
  authors: [{ name: 'SupplyNexus' }],
  robots: 'noindex, nofollow', // Private admin dashboard
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
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
          <CssBaseline />
          <ClientThemeProvider>
            <QueryProvider>
              <AuthProvider>
                <EnvironmentBadge />
                {children}
              </AuthProvider>
            </QueryProvider>
          </ClientThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
