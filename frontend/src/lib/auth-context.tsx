'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';

import { authApi } from '@/lib/api';
import { User, LoginCredentials } from '@/types/auth';
import { tokenManager } from '@/lib/token-manager';
import { frontendLogger } from '@/lib/frontend-logger';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // 检查是否在浏览器环境
  const isBrowser = typeof window !== 'undefined';

  const checkAuth = useCallback(async () => {
    try {
      frontendLogger.info('AuthContext: Checking authentication status');

      // 添加tokenManager状态调试
      const accessToken = tokenManager.getAccessToken();
      const refreshToken = tokenManager.getRefreshToken();

      frontendLogger.info('AuthContext: TokenManager state', {
        hasAccessToken: !!accessToken,
        hasRefreshToken: !!refreshToken,
        accessTokenLength: accessToken ? accessToken.length : 0,
        refreshTokenLength: refreshToken ? refreshToken.length : 0,
      });

      if (!tokenManager.isLoggedIn()) {
        frontendLogger.info('AuthContext: User not logged in');
        setIsLoading(false);
        return;
      }

      frontendLogger.info(
        'AuthContext: User appears to be logged in, getting profile'
      );
      const userData = await authApi.getProfile();

      frontendLogger.info('AuthContext: Profile retrieved successfully', {
        hasUserData: !!userData,
        userId: userData?.id,
      });

      setUser(userData);
    } catch (error) {
      frontendLogger.error('AuthContext: Authentication check failed', {
        error: String(error),
      });

      tokenManager.clearTokens();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const login = async (credentials: LoginCredentials) => {
    try {
      frontendLogger.info('AuthContext: Starting login process');
      setIsLoading(true);

      frontendLogger.info('AuthContext: Calling authApi.login');
      const response = await authApi.login(credentials);

      frontendLogger.info('AuthContext: Login API call completed', {
        hasResponse: !!response,
        responseKeys: response ? Object.keys(response) : [],
      });

      // token管理器已经在API调用中自动存储了token
      // 这里不需要额外操作

      // Get user data after successful login
      frontendLogger.info('AuthContext: Getting user profile');
      const userData = await authApi.getProfile();

      frontendLogger.info('AuthContext: User profile retrieved', {
        hasUserData: !!userData,
        userId: userData?.id,
        userEmail: userData?.email,
      });

      setUser(userData);

      frontendLogger.info(
        'AuthContext: Login successful, redirecting to dashboard'
      );
      toast.success('登录成功');
      router.push('/dashboard');
    } catch (error: any) {
      frontendLogger.error('AuthContext: Login failed', {
        error: String(error),
        errorMessage: error.message,
        errorResponse: error.response?.data,
        errorCode: error.code,
        errorStack: error.stack,
        errorType: error.constructor.name,
        hasResponse: !!error.response,
        responseStatus: error.response?.status,
        responseStatusText: error.response?.statusText,
      });

      toast.error(error.response?.data?.detail || '登录失败');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    tokenManager.clearTokens();
    setUser(null);
    toast.success('已退出登录');
    router.push('/auth/login');
  };

  useEffect(() => {
    if (isBrowser) {
      checkAuth();
    } else {
      setIsLoading(false);
    }
  }, [isBrowser, checkAuth]);

  const value = {
    user,
    isLoading,
    login,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
