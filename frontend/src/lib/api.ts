import axios, { AxiosResponse } from 'axios';
import toast from 'react-hot-toast';

import { LoginCredentials, TokenResponse } from '@/types/auth';
import { tokenManager } from './token-manager';
import { frontendLogger } from './frontend-logger';

// Create axios instance for frontend API routes
export const frontendApi = axios.create({
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
    // 记录错误信息
    frontendLogger.error('API request failed', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      url: error.config?.url,
      method: error.config?.method,
      errorMessage: error.message,
      errorData: error.response?.data,
    });

    if (error.response?.status === 401) {
      // 检查是否是签名验证错误
      const errorDetail = error.response?.data?.detail;
      if (errorDetail === 'Invalid signature') {
        // 签名验证错误，不自动logout，让用户手动处理
        toast.error('签名验证失败，请检查网络连接或联系管理员');
        return Promise.reject(error);
      }

      // 防止无限重试：检查是否已经重试过
      if (error.config._retry) {
        // 如果已经重试过，直接清除token并重定向
        tokenManager.clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
          toast.error('登录已过期，请重新登录');
        }
        return Promise.reject(error);
      }

      // 标记为已重试
      error.config._retry = true;

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
    } else if (error.response?.status >= 500) {
      // 服务器错误，显示友好错误信息
      toast.error('服务器错误，请稍后重试或联系管理员');
    } else if (error.response?.status >= 400) {
      // 客户端错误，显示具体错误信息
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        '请求失败';
      toast.error(errorMessage);
    } else if (
      error.code === 'NETWORK_ERROR' ||
      error.message === 'Network Error'
    ) {
      // 网络错误
      toast.error('网络连接失败，请检查网络连接');
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
