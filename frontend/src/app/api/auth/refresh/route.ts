import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';

const logger = createLogger('auth.refresh');

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  logger.requestStart(request.method, request.url);

  try {
    // 解析请求体
    const body = await request.json();
    const { refresh_token } = body;

    if (!refresh_token) {
      logger.warn('Missing refresh token');
      return NextResponse.json(
        { error: 'Refresh token is required' },
        { status: 400 }
      );
    }

    try {
      // 验证refresh token
      const refreshPayload = jwtUtilsServer.verifyToken(refresh_token);

      logger.info('Refresh token verified successfully', {
        userId: refreshPayload.sub,
        tenantId: refreshPayload.tenant_id,
        tenantName: refreshPayload.tenant_name,
        email: refreshPayload.email,
      });

      // 生成新的token对
      const newAccessToken = jwtUtilsServer.generateToken(
        {
          sub: refreshPayload.sub,
          tenant_id: refreshPayload.tenant_id,
          email: refreshPayload.email,
          tenant_name: refreshPayload.tenant_name,
          type: 'access',
        },
        3600
      ); // 1 hour

      const newRefreshToken = jwtUtilsServer.generateToken(
        {
          sub: refreshPayload.sub,
          tenant_id: refreshPayload.tenant_id,
          email: refreshPayload.email,
          tenant_name: refreshPayload.tenant_name,
          type: 'refresh',
        },
        7 * 24 * 3600
      ); // 7 days

      const newTokens = {
        access_token: newAccessToken,
        refresh_token: newRefreshToken,
        token_type: 'bearer',
        user: {
          id: parseInt(refreshPayload.sub),
          email: refreshPayload.email,
          tenant_id: refreshPayload.tenant_id,
          is_active: true,
        },
        tenant_name: refreshPayload.tenant_name,
      };

      const duration = Date.now() - startTime;
      logger.requestComplete(request.method, request.url, 200, duration);

      return NextResponse.json(newTokens);
    } catch (jwtError) {
      logger.error('Refresh token verification failed', {
        error: String(jwtError),
      });
      return NextResponse.json(
        { error: 'Invalid or expired refresh token' },
        { status: 401 }
      );
    }
  } catch (error) {
    logger.error('Token refresh request error', {
      error: error instanceof Error ? error.message : 'Unknown error',
    });
    const duration = Date.now() - startTime;
    logger.requestError(
      request.method,
      request.url,
      error instanceof Error ? error : new Error('Unknown error'),
      duration
    );
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
