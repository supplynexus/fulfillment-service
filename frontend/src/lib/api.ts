import axios, { AxiosResponse } from 'axios';
import toast from 'react-hot-toast';

import { User, LoginCredentials, TokenResponse } from '@/types/auth';
import { Customer, CustomerCreate } from '@/types/customer';
import { Order, OrderCreate } from '@/types/order';
import { Product } from '@/types/product';
import { DashboardStats } from '@/types/dashboard';
import { tokenManager } from './token-manager';
import { frontendLogger } from './frontend-logger';

// Create axios instance for frontend API routes
const frontendApi = axios.create({
  baseURL: '', // Empty baseURL for frontend API routes
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token for frontend API
frontendApi.interceptors.request.use(
  async config => {
    try {
      // 使用token管理器获取有效的access token
      const accessToken = await tokenManager.getValidAccessToken();
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
      }
    } catch (error) {
      console.error('Failed to get valid access token:', error);
      // 如果获取token失败，清除所有token并重定向到登录页
      tokenManager.clearTokens();
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Response interceptor for frontend API
frontendApi.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // 如果是401错误，尝试刷新token
      try {
        await tokenManager.refreshTokens();
        // 重新发送原始请求
        const originalRequest = error.config;
        const accessToken = await tokenManager.getValidAccessToken();
        if (accessToken) {
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          return frontendApi(originalRequest);
        }
      } catch (refreshError) {
        // 如果刷新失败，清除token并重定向到登录页
        tokenManager.clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
          toast.error('登录已过期，请重新登录');
        }
      }
    }
    return Promise.reject(error);
  }
);

// Create axios instance for backend API
const backendApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
backendApi.interceptors.request.use(
  async config => {
    try {
      const accessToken = await tokenManager.getValidAccessToken();
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
      }
    } catch (error) {
      console.error('Failed to get valid access token:', error);
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Response interceptor for global error handling
backendApi.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401) {
      // 如果是401错误，尝试刷新token
      try {
        await tokenManager.refreshTokens();
        // 重新发送原始请求
        const originalRequest = error.config;
        const accessToken = await tokenManager.getValidAccessToken();
        if (accessToken) {
          originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          return backendApi(originalRequest);
        }
      } catch (refreshError) {
        // 如果刷新失败，清除token并重定向到登录页
        tokenManager.clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
          toast.error('登录已过期，请重新登录');
        }
      }
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    try {
      frontendLogger.info('Starting login process', {
        username: credentials.username,
        tenantName: credentials.tenantName,
      });

      // 发送登录请求到前端 API 路由，服务器端会处理签名生成
      const formData = new FormData();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);
      formData.append('tenant_name', credentials.tenantName);

      frontendLogger.info('Sending login request to frontend API');

      // 创建一个新的axios实例，不继承默认的Content-Type
      const loginApi = axios.create({
        baseURL: '',
        timeout: 10000,
      });

      const response: AxiosResponse<TokenResponse> = await loginApi.post(
        '/api/auth/login',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      frontendLogger.info('Login API response received', {
        status: response.status,
        hasData: !!response.data,
        dataKeys: response.data ? Object.keys(response.data) : [],
        responseHeaders: Object.keys(response.headers || {}),
      });

      // 检查响应数据
      if (!response.data) {
        frontendLogger.error('Login API response has no data');
        throw new Error('Login API response has no data');
      }

      if (!response.data.access_token) {
        frontendLogger.error('Login API response missing access_token', {
          dataKeys: Object.keys(response.data),
          data: response.data,
        });
        throw new Error('Login API response missing access_token');
      }

      // 使用token管理器存储token
      frontendLogger.info('Storing tokens in token manager', {
        accessTokenLength: response.data.access_token?.length,
        refreshTokenLength: response.data.refresh_token?.length,
        hasUser: !!response.data.user,
      });

      tokenManager.storeTokens(response.data);

      frontendLogger.info('Login process completed successfully');

      return response.data;
    } catch (error) {
      frontendLogger.error('Login process failed', {
        error: String(error),
        errorMessage: error instanceof Error ? error.message : 'Unknown error',
        errorStack: error instanceof Error ? error.stack : undefined,
        errorCode: (error as any)?.code,
        errorResponse: (error as any)?.response?.data,
      });
      console.error('Login error:', error);
      throw error;
    }
  },

  // 其他 API 调用使用 frontendApi
  getProfile: async (): Promise<any> => {
    const response = await frontendApi.get('/api/users/me');
    return response.data;
  },

  refreshToken: async (): Promise<TokenResponse> => {
    const newTokens = await tokenManager.refreshTokens();
    return newTokens;
  },

  logout: async (): Promise<void> => {
    // 清除本地存储的token
    tokenManager.clearTokens();
  },
};

// Customers API
export const customersApi = {
  getAll: async (skip = 0, limit = 100): Promise<Customer[]> => {
    const response: AxiosResponse<Customer[]> = await backendApi.get(
      '/api/v1/customers',
      {
        params: { skip, limit },
      }
    );
    return response.data;
  },

  getById: async (id: number): Promise<Customer> => {
    const response: AxiosResponse<Customer> = await backendApi.get(
      `/api/v1/customers/${id}`
    );
    return response.data;
  },

  create: async (customer: CustomerCreate): Promise<Customer> => {
    const response: AxiosResponse<Customer> = await backendApi.post(
      '/api/v1/customers',
      customer
    );
    return response.data;
  },

  update: async (
    id: number,
    customer: Partial<CustomerCreate>
  ): Promise<Customer> => {
    const response: AxiosResponse<Customer> = await backendApi.put(
      `/api/v1/customers/${id}`,
      customer
    );
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await backendApi.delete(`/api/v1/customers/${id}`);
  },
};

// Orders API
export const ordersApi = {
  getAll: async (params?: {
    skip?: number;
    limit?: number;
    customer_id?: number;
    status?: string;
  }): Promise<Order[]> => {
    const response: AxiosResponse<Order[]> = await backendApi.get(
      '/api/v1/orders',
      { params }
    );
    return response.data;
  },

  getById: async (id: number): Promise<Order> => {
    const response: AxiosResponse<Order> = await backendApi.get(
      `/api/v1/orders/${id}`
    );
    return response.data;
  },

  create: async (order: OrderCreate): Promise<Order> => {
    const response: AxiosResponse<Order> = await backendApi.post(
      '/api/v1/orders',
      order
    );
    return response.data;
  },

  retryFulfillment: async (id: number): Promise<void> => {
    await backendApi.post(`/api/v1/orders/${id}/retry`);
  },
};

// Products API
export const productsApi = {
  getAll: async (skip = 0, limit = 100): Promise<Product[]> => {
    const response: AxiosResponse<Product[]> = await backendApi.get(
      '/api/v1/products',
      {
        params: { skip, limit },
      }
    );
    return response.data;
  },

  syncCatalog: async (): Promise<{ message: string; task_id: string }> => {
    const response = await backendApi.get('/api/v1/products/catalog');
    return response.data;
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response: AxiosResponse<DashboardStats> = await backendApi.get(
      '/api/v1/dashboard/stats'
    );
    return response.data;
  },

  getRecentOrders: async (limit = 10): Promise<Order[]> => {
    const response: AxiosResponse<Order[]> = await backendApi.get(
      '/api/v1/dashboard/orders/recent',
      {
        params: { limit },
      }
    );
    return response.data;
  },

  getMetrics: async (days = 30): Promise<any> => {
    const response = await backendApi.get('/api/v1/dashboard/metrics', {
      params: { days },
    });
    return response.data;
  },
};

export default backendApi;
