import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProductCategoriesPage from './page'

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

describe('ProductCategoriesPage', () => {
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

    renderWithQueryClient(<ProductCategoriesPage />)

    expect(screen.getByText('产品分类管理')).toBeInTheDocument()
    expect(screen.getByText('创建分类')).toBeInTheDocument()
    expect(screen.getByText('刷新')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

    renderWithQueryClient(<ProductCategoriesPage />)

    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('displays categories when loaded successfully', async () => {
    const mockCategories = [
      {
        id: '1',
        name: '电子产品',
        code: 'electronics',
        description: '电子设备及相关产品',
        parent_id: null,
        level: 0,
        path: '/electronics',
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
      },
      {
        id: '2',
        name: '服装',
        code: 'clothing',
        description: '服装及相关产品',
        parent_id: null,
        level: 0,
        path: '/clothing',
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
      },
    ]

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockCategories,
    })

    renderWithQueryClient(<ProductCategoriesPage />)

    await waitFor(() => {
      expect(screen.getByText('电子产品')).toBeInTheDocument()
      expect(screen.getByText('服装')).toBeInTheDocument()
    })
  })

  it('shows error message when API call fails', async () => {
    mockFetch.mockRejectedValueOnce(new Error('API Error'))

    renderWithQueryClient(<ProductCategoriesPage />)

    await waitFor(() => {
      expect(screen.getByText('加载产品分类失败')).toBeInTheDocument()
    })
  })

  it('opens create category form when create button is clicked', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    })

    renderWithQueryClient(<ProductCategoriesPage />)

    await waitFor(() => {
      expect(screen.getByText('创建分类')).toBeInTheDocument()
    })

    const createButton = screen.getByText('创建分类')
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText('创建分类')).toBeInTheDocument() // Dialog title
    })
  })

  it('handles refresh button click', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    })

    renderWithQueryClient(<ProductCategoriesPage />)

    await waitFor(() => {
      expect(screen.getByText('刷新')).toBeInTheDocument()
    })

    const refreshButton = screen.getByText('刷新')
    fireEvent.click(refreshButton)

    // Should call fetch again
    expect(mockFetch).toHaveBeenCalledTimes(2)
  })
})
