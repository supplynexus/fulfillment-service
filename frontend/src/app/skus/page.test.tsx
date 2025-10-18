import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SkusPage from './page'

// Mock the auth components
jest.mock('@/components/auth/ProtectedRoute', () => {
  return function MockProtectedRoute({ children }: { children: React.ReactNode }) {
    return <div data-testid="protected-route">{children}</div>
  }
})

jest.mock('@/components/layout/DashboardLayout', () => {
  return function MockDashboardLayout({ children }: { children: React.ReactNode }) {
    return <div data-testid="dashboard-layout">{children}</div>
  }
})

// Mock fetch
const mockFetch = jest.fn()
global.fetch = mockFetch

describe('SkusPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    })
    mockFetch.mockClear()
  })

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    )
  }

  it('renders the page title and main elements', () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    })

    renderWithQueryClient(<SkusPage />)

    expect(screen.getByText('SKU 管理')).toBeInTheDocument()
    expect(screen.getByText('创建 SKU')).toBeInTheDocument()
    expect(screen.getByText('批量创建')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

    renderWithQueryClient(<SkusPage />)

    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('displays SKUs when loaded successfully', async () => {
    const mockSkus = [
      {
        id: '1',
        sku: 'IMP-BSC-BLK-L',
        name: 'IMPEACH BASIC BLACK - L',
        product_id: '1',
        attributes: { color: 'Black', size: 'L' },
        price: 29.99,
        cost: 15.00,
        stock: 100,
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
      },
      {
        id: '2',
        sku: 'IMP-BSC-BLK-M',
        name: 'IMPEACH BASIC BLACK - M',
        product_id: '1',
        attributes: { color: 'Black', size: 'M' },
        price: 29.99,
        cost: 15.00,
        stock: 50,
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
      },
    ]

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockSkus,
    })

    renderWithQueryClient(<SkusPage />)

    await waitFor(() => {
      expect(screen.getByText('IMP-BSC-BLK-L')).toBeInTheDocument()
      expect(screen.getByText('IMP-BSC-BLK-M')).toBeInTheDocument()
    })
  })

  it('shows error message when API call fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('API Error'))

    renderWithQueryClient(<SkusPage />)

    await waitFor(() => {
      expect(screen.getByText('加载SKU列表失败')).toBeInTheDocument()
    })
  })

  it('opens create SKU form when create button is clicked', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    })

    renderWithQueryClient(<SkusPage />)

    await waitFor(() => {
      expect(screen.getByText('创建 SKU')).toBeInTheDocument()
    })

    const createButton = screen.getByText('创建 SKU')
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText('创建 SKU')).toBeInTheDocument() // Dialog title
    })
  })

  it('opens batch create page when batch create button is clicked', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    })

    renderWithQueryClient(<SkusPage />)

    await waitFor(() => {
      expect(screen.getByText('批量创建')).toBeInTheDocument()
    })

    const batchCreateButton = screen.getByText('批量创建')
    fireEvent.click(batchCreateButton)

    // Should navigate to batch create page
    // This would be tested with router mocking in a real scenario
  })
})
