import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';

const logger = createLogger('auth.refresh');

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  logger.requestStart(request.method, request.url);
  
  try {
    const body = await request.json();
    const { refresh_token } = body;

    if (!refresh_token) {
      logger.warn('Missing refresh token in request');
      return NextResponse.json(
        { error: 'Refresh token is required' },
        { status: 400 }
      );
    }

    logger.info('Token refresh attempt', { hasRefreshToken: !!refresh_token });

    // 转发到后端 API
    const backendResponse = await fetch('http://localhost:8000/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token }),
    });

    const responseData = await backendResponse.json();

    if (backendResponse.ok) {
      logger.info('Token refresh successful');
      const duration = Date.now() - startTime;
      logger.requestComplete(request.method, request.url, backendResponse.status, duration);
      return NextResponse.json(responseData);
    } else {
      logger.warn('Token refresh failed', { 
        status: backendResponse.status,
        error: responseData.detail || responseData.error 
      });
      const duration = Date.now() - startTime;
      logger.requestError(request.method, request.url, new Error(responseData.detail || 'Token refresh failed'), duration);
      return NextResponse.json(
        { error: responseData.detail || 'Token refresh failed' },
        { status: backendResponse.status }
      );
    }
  } catch (error) {
    logger.error('Token refresh error', { error: error instanceof Error ? error.message : 'Unknown error' });
    const duration = Date.now() - startTime;
    logger.requestError(request.method, request.url, error instanceof Error ? error : new Error('Unknown error'), duration);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
