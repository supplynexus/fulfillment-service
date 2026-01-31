import { NextRequest } from 'next/server'
import { GET, POST } from './route'

// Mock the backend API
jest.mock('@/lib/api', () => ({
  backendApi: {
    get: jest.fn(),
    post: jest.fn(),
  },
}))

import { backendApi } from '@/lib/api'

describe('/api/product-categories', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('GET', () => {
    it('should return categories when API call succeeds', async () => {
      const mockCategories = [
        {
          id: '1',
          name: '电子产品',
          code: 'electronics',
          description: '电子设备及相关产品',
        },
      ]

      ;(backendApi.get as jest.Mock).mockResolvedValueOnce({
        data: mockCategories,
        status: 200,
      })

      const request = new NextRequest('http://localhost:3000/api/product-categories', {
        headers: {
          authorization: 'Bearer mock-token',
        },
      })

      const response = await GET(request)
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data).toEqual(mockCategories)
      expect(backendApi.get).toHaveBeenCalledWith('/api/v1/product-categories/', {
        headers: {
          Authorization: 'Bearer mock-token',
        },
      })
    })

    it('should return 401 when no authorization header', async () => {
      const request = new NextRequest('http://localhost:3000/api/product-categories')

      const response = await GET(request)
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data.error).toBe('未找到认证信息')
    })

    it('should return 500 when API call fails', async () => {
      ;(backendApi.get as jest.Mock).mockRejectedValueOnce(new Error('API Error'))

      const request = new NextRequest('http://localhost:3000/api/product-categories', {
        headers: {
          authorization: 'Bearer mock-token',
        },
      })

      const response = await GET(request)
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data.error).toBe('获取产品分类失败')
    })
  })

  describe('POST', () => {
    it('should create category when API call succeeds', async () => {
      const mockCategory = {
        name: '新分类',
        code: 'new-category',
        description: '新分类描述',
      }

      ;(backendApi.post as jest.Mock).mockResolvedValueOnce({
        data: { id: '1', ...mockCategory },
        status: 201,
      })

      const request = new NextRequest('http://localhost:3000/api/product-categories', {
        method: 'POST',
        headers: {
          authorization: 'Bearer mock-token',
          'content-type': 'application/json',
        },
        body: JSON.stringify(mockCategory),
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(201)
      expect(data).toEqual({ id: '1', ...mockCategory })
      expect(backendApi.post).toHaveBeenCalledWith('/api/v1/product-categories/', mockCategory, {
        headers: {
          Authorization: 'Bearer mock-token',
        },
      })
    })

    it('should return 401 when no authorization header', async () => {
      const request = new NextRequest('http://localhost:3000/api/product-categories', {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
        },
        body: JSON.stringify({ name: 'Test' }),
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data.error).toBe('未找到认证信息')
    })

    it('should return 500 when API call fails', async () => {
      ;(backendApi.post as jest.Mock).mockRejectedValueOnce(new Error('API Error'))

      const request = new NextRequest('http://localhost:3000/api/product-categories', {
        method: 'POST',
        headers: {
          authorization: 'Bearer mock-token',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ name: 'Test' }),
      })

      const response = await POST(request)
      const data = await response.json()

      expect(response.status).toBe(500)
      expect(data.error).toBe('创建产品分类失败')
    })
  })
})
