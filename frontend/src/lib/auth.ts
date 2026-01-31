import { jwtDecode } from 'jwt-decode';

// Token 类型定义
export interface JWTPayload {
  sub: string;
  tenant_id: number;
  exp: number;
  type: 'access' | 'refresh';
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  tenant_name?: string; // 添加 tenant_name
}

export interface TenantInfo {
  id: number;
  name: string;
  display_name?: string;
}

// Token 管理类
class TokenManager {
  private static instance: TokenManager;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private tokenType: string = 'bearer';
  private tenantName: string | null = null; // 添加 tenant_name

  private constructor() {
    // 从 localStorage 恢复 token
    this.loadTokensFromStorage();
  }

  static getInstance(): TokenManager {
    if (!TokenManager.instance) {
      TokenManager.instance = new TokenManager();
    }
    return TokenManager.instance;
  }

  // 检查是否在浏览器环境
  private isBrowser(): boolean {
    return typeof window !== 'undefined' && typeof localStorage !== 'undefined';
  }

  // 保存 tokens 到 localStorage
  private saveTokensToStorage(tokens: AuthTokens): void {
    if (!this.isBrowser()) return;

    try {
      localStorage.setItem('auth_tokens', JSON.stringify(tokens));
    } catch (error) {
      console.error('Failed to save tokens to localStorage:', error);
    }
  }

  // 从 localStorage 加载 tokens
  private loadTokensFromStorage(): void {
    if (!this.isBrowser()) return;

    try {
      const tokensStr = localStorage.getItem('auth_tokens');
      if (tokensStr) {
        const tokens: AuthTokens = JSON.parse(tokensStr);
        this.accessToken = tokens.access_token;
        this.refreshToken = tokens.refresh_token;
        this.tokenType = tokens.token_type;
        this.tenantName = tokens.tenant_name || null; // 加载 tenant_name
      }
    } catch (error) {
      console.error('Failed to load tokens from localStorage:', error);
      this.clearTokens();
    }
  }

  // 设置 tokens
  setTokens(tokens: AuthTokens): void {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    this.tokenType = tokens.token_type;
    this.tenantName = tokens.tenant_name || null; // 保存 tenant_name
    this.saveTokensToStorage(tokens);
  }

  // 获取 access token
  getAccessToken(): string | null {
    return this.accessToken;
  }

  // 获取 refresh token
  getRefreshToken(): string | null {
    return this.refreshToken;
  }

  // 获取 token type
  getTokenType(): string {
    return this.tokenType;
  }

  // 获取 tenant name
  getTenantName(): string | null {
    return this.tenantName;
  }

  // 检查 token 是否过期
  isTokenExpired(token: string): boolean {
    try {
      const decoded = jwtDecode<JWTPayload>(token);
      const currentTime = Math.floor(Date.now() / 1000);
      return decoded.exp < currentTime;
    } catch (error) {
      console.error('Failed to decode token:', error);
      return true;
    }
  }

  // 检查 access token 是否有效
  isAccessTokenValid(): boolean {
    if (!this.accessToken) return false;
    return !this.isTokenExpired(this.accessToken);
  }

  // 检查 refresh token 是否有效
  isRefreshTokenValid(): boolean {
    if (!this.refreshToken) return false;
    return !this.isTokenExpired(this.refreshToken);
  }

  // 获取当前用户信息
  getCurrentUser(): { userId: string; tenantId: number } | null {
    if (!this.accessToken) return null;

    try {
      const decoded = jwtDecode<JWTPayload>(this.accessToken);
      return {
        userId: decoded.sub,
        tenantId: decoded.tenant_id,
      };
    } catch (error) {
      console.error('Failed to decode access token:', error);
      return null;
    }
  }

  // 清除所有 tokens
  clearTokens(): void {
    this.accessToken = null;
    this.refreshToken = null;
    this.tokenType = 'bearer';
    this.tenantName = null; // 清除 tenant_name
    if (this.isBrowser()) {
      localStorage.removeItem('auth_tokens');
    }
  }

  // 刷新 access token
  async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken || !this.isRefreshTokenValid()) {
      this.clearTokens();
      return false;
    }

    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: this.refreshToken,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        this.accessToken = data.access_token;
        if (this.accessToken && this.refreshToken) {
          this.saveTokensToStorage({
            access_token: this.accessToken,
            refresh_token: this.refreshToken,
            token_type: this.tokenType,
          });
        }
        return true;
      } else {
        this.clearTokens();
        return false;
      }
    } catch (error) {
      console.error('Failed to refresh access token:', error);
      this.clearTokens();
      return false;
    }
  }
}

// 导出单例实例
export const tokenManager = TokenManager.getInstance();

// API 客户端配置
export const createAuthenticatedApiClient = () => {
  // 前端 API 客户端应该调用前端的 API 路由，而不是直接调用后端
  const baseURL = '';

  const client = {
    // 获取认证头
    getAuthHeaders: async (): Promise<Record<string, string>> => {
      // 检查 access token 是否有效
      if (!tokenManager.isAccessTokenValid()) {
        // 尝试刷新 token
        const refreshed = await tokenManager.refreshAccessToken();
        if (!refreshed) {
          throw new Error('Authentication required');
        }
      }

      const accessToken = tokenManager.getAccessToken();
      if (!accessToken) {
        throw new Error('No access token available');
      }

      return {
        Authorization: `${tokenManager.getTokenType()} ${accessToken}`,
      };
    },

    // 发送请求到前端 API 路由
    request: async <T>(
      endpoint: string,
      options: RequestInit = {}
    ): Promise<T> => {
      const authHeaders = await client.getAuthHeaders();

      const response = await fetch(`${baseURL}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
          ...options.headers,
        },
      });

      if (response.status === 401) {
        // Token 可能过期，尝试刷新
        const refreshed = await tokenManager.refreshAccessToken();
        if (refreshed) {
          // 重试请求
          const newAuthHeaders = await client.getAuthHeaders();
          const retryResponse = await fetch(`${baseURL}${endpoint}`, {
            ...options,
            headers: {
              'Content-Type': 'application/json',
              ...newAuthHeaders,
              ...options.headers,
            },
          });

          if (!retryResponse.ok) {
            throw new Error(`API request failed: ${retryResponse.statusText}`);
          }

          return retryResponse.json();
        } else {
          // 刷新失败，清除 tokens
          tokenManager.clearTokens();
          throw new Error('Authentication failed');
        }
      }

      if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
      }

      return response.json();
    },

    // GET 请求
    get: <T>(endpoint: string): Promise<T> => {
      return client.request<T>(endpoint, { method: 'GET' });
    },

    // POST 请求
    post: <T>(endpoint: string, data?: any): Promise<T> => {
      return client.request<T>(endpoint, {
        method: 'POST',
        body: data ? JSON.stringify(data) : undefined,
      });
    },

    // PUT 请求
    put: <T>(endpoint: string, data?: any): Promise<T> => {
      return client.request<T>(endpoint, {
        method: 'PUT',
        body: data ? JSON.stringify(data) : undefined,
      });
    },

    // DELETE 请求
    delete: <T>(endpoint: string): Promise<T> => {
      return client.request<T>(endpoint, { method: 'DELETE' });
    },
  };

  return client;
};

// 导出 API 客户端实例
export const apiClient = createAuthenticatedApiClient();
