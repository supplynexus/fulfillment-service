import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { backendApi } from '@/lib/api';

const logger = createLogger('api.product-variants');

export async function GET(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    logger.requestStart(request.method, request.url);
    
    // 1. 验证前端JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      logger.error('Invalid frontend token', { error: String(error) });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Frontend JWT verified successfully', {
      userId,
      tenantName,
    });

    // 2. 构建查询参数
    const { searchParams } = new URL(request.url);
    const queryParams = new URLSearchParams();
    
    // 添加查询参数
    searchParams.forEach((value, key) => {
      queryParams.append(key, value);
    });
    
    const url = `/api/v1/product-variants/?${queryParams.toString()}`;
    
    // 3. 调用后端API
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
    const fullUrl = `${backendUrl}${url}`;
    
    logger.info('Calling backend API', { fullUrl });
    
    const response = await fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    logger.requestComplete(request.method, request.url, 200, Date.now() - startTime);
    return NextResponse.json(data);
    
  } catch (error: any) {
    logger.error('API request failed', { error: String(error) });
    return NextResponse.json(
      { error: '获取产品变体失败' },
      { status: error.response?.status || 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    logger.requestStart(request.method, request.url);
    
    // 1. 验证前端JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      logger.error('Invalid frontend token', { error: String(error) });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Frontend JWT verified successfully', {
      userId,
      tenantName,
    });

    // 2. 获取请求体
    const body = await request.json();
    
    // 3. 调用后端API
    const response = await backendApi.post('/api/v1/product-variants/', body);
    
    logger.requestComplete(request.method, request.url, 201, Date.now() - startTime);
    return NextResponse.json(response.data, { status: 201 });
    
  } catch (error: any) {
    logger.error('API request failed', { error: String(error) });
    return NextResponse.json(
      { error: '创建产品变体失败' },
      { status: error.response?.status || 500 }
    );
  }
}
