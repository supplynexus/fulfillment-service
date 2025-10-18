import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { backendApi } from '@/lib/api';

const logger = createLogger('api.product-categories');

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
      logger.info('Attempting to verify JWT token', { 
        tokenLength: frontendToken.length,
        tokenPrefix: frontendToken.substring(0, 50) + '...'
      });
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
      logger.info('JWT token verified successfully', { 
        userId: decodedToken.sub,
        tenantName: decodedToken.tenant_name
      });
    } catch (error) {
      logger.error('Invalid frontend token', { 
        error: String(error),
        tokenLength: frontendToken.length,
        tokenPrefix: frontendToken.substring(0, 50) + '...'
      });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;

    // 2. 构建查询参数
    const { searchParams } = new URL(request.url);
    const queryParams = new URLSearchParams();
    
    // 添加查询参数
    searchParams.forEach((value, key) => {
      queryParams.append(key, value);
    });
    
    const url = `/api/v1/product-categories/?${queryParams.toString()}`;
    
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
      { error: '获取产品分类失败' },
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
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
    const fullUrl = `${backendUrl}/api/v1/product-categories/`;
    
    logger.info('Calling backend API', { fullUrl, body });
    
    const response = await fetch(fullUrl, {
      method: 'POST',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      logger.error('Backend API error', { 
        status: response.status, 
        statusText: response.statusText,
        error: errorData
      });
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    logger.requestComplete(request.method, request.url, 201, Date.now() - startTime);
    return NextResponse.json(data, { status: 201 });
    
  } catch (error: any) {
    logger.error('API request failed', { error: String(error) });
    return NextResponse.json(
      { error: '创建产品分类失败' },
      { status: error.response?.status || 500 }
    );
  }
}
