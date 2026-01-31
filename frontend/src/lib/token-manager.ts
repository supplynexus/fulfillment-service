import { jwtUtils } from './jwt-utils';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    tenant_id: number;
    is_active: boolean;
  };
  tenant_name: string;
}

export interface JWTPayload {
  sub: string;
  tenant_id: number;
  email: string;
  tenant_name: string;
  type: 'access' | 'refresh';
  exp: number;
  iat: number;
}

class TokenManager {
  private static instance: TokenManager;
  private refreshPromise: Promise<TokenPair> | null = null;

  private constructor() {}

  public static getInstance(): TokenManager {
    if (!TokenManager.instance) {
      TokenManager.instance = new TokenManager();
    }
    return TokenManager.instance;
  }

  /**
   * 存储token到localStorage
   */
  public storeTokens(tokens: TokenPair): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      localStorage.setItem('user', JSON.stringify(tokens.user));
      localStorage.setItem('tenant_name', tokens.tenant_name);
      localStorage.setItem('token_type', tokens.token_type);

      // 添加调试日志
      console.log('[TokenManager] Tokens stored successfully', {
        hasAccessToken: !!tokens.access_token,
        hasRefreshToken: !!tokens.refresh_token,
        hasUser: !!tokens.user,
        tenantName: tokens.tenant_name,
      });
    }
  }

  /**
   * 从localStorage获取access token
   */
  public getAccessToken(): string | null {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      console.log('🔍 TokenManager.getAccessToken:', {
        hasToken: !!token,
        tokenLength: token?.length,
        tokenPrefix: token?.substring(0, 20) + '...',
      });
      return token;
    }
    return null;
  }

  /**
   * 从localStorage获取refresh token
   */
  public getRefreshToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('refresh_token');
    }
    return null;
  }

  /**
   * 获取用户信息
   */
  public getUser(): any {
    if (typeof window !== 'undefined') {
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    }
    return null;
  }

  /**
   * 获取租户名称
   */
  public getTenantName(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('tenant_name');
    }
    return null;
  }

  /**
   * 清除所有token
   */
  public clearTokens(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      localStorage.removeItem('tenant_name');
      localStorage.removeItem('token_type');
    }
  }

  /**
   * 检查用户是否已登录
   */
  public isLoggedIn(): boolean {
    const accessToken = this.getAccessToken();

    // 添加调试日志
    console.log('[TokenManager] Checking login status', {
      hasAccessToken: !!accessToken,
      accessTokenLength: accessToken ? accessToken.length : 0,
    });

    if (!accessToken) {
      console.log('[TokenManager] No access token found');
      return false;
    }

    // 检查token是否过期
    if (this.isTokenExpired(accessToken)) {
      console.log('[TokenManager] Access token expired, clearing tokens');
      this.clearTokens();
      return false;
    }

    console.log('[TokenManager] User is logged in');
    return true;
  }

  /**
   * 检查token是否即将过期（提前5分钟刷新）
   */
  public isTokenExpiringSoon(
    token: string,
    bufferMinutes: number = 5
  ): boolean {
    return jwtUtils.isTokenExpiringSoon(token, bufferMinutes);
  }

  /**
   * 检查token是否已过期
   */
  public isTokenExpired(token: string): boolean {
    return jwtUtils.isTokenExpired(token);
  }

  /**
   * 刷新token（通过API调用）
   */
  public async refreshTokens(): Promise<TokenPair> {
    // 如果已经有刷新请求在进行中，返回同一个promise
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this.performRefresh();

    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.refreshPromise = null;
    }
  }

  /**
   * 执行实际的刷新操作（通过API调用）
   */
  private async performRefresh(): Promise<TokenPair> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      // 验证refresh token（客户端解码，不验证签名）
      // const refreshPayload = jwtUtils.decodeToken(refreshToken) as JWTPayload;

      // 检查refresh token是否过期
      if (jwtUtils.isTokenExpired(refreshToken)) {
        throw new Error('Refresh token expired');
      }

      // 通过API调用刷新token
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to refresh token');
      }

      const newTokens: TokenPair = await response.json();

      // 存储新的token
      this.storeTokens(newTokens);

      return newTokens;
    } catch {
      // 如果刷新失败，清除所有token
      this.clearTokens();
      throw new Error('Refresh token expired');
    }
  }

  /**
   * 获取有效的access token，如果即将过期则自动刷新
   */
  public async getValidAccessToken(): Promise<string> {
    const accessToken = this.getAccessToken();

    if (!accessToken) {
      throw new Error('No access token available');
    }

    // 检查是否即将过期
    if (this.isTokenExpiringSoon(accessToken)) {
      try {
        const newTokens = await this.refreshTokens();
        return newTokens.access_token;
      } catch (error) {
        // 如果刷新失败，尝试使用当前token
        if (!this.isTokenExpired(accessToken)) {
          return accessToken;
        }
        throw error;
      }
    }

    return accessToken;
  }
}

// 导出单例实例
export const tokenManager = TokenManager.getInstance();
