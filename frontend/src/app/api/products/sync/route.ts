import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.products.sync');

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
      contentType: request.headers.get('content-type'),
    });

    // 验证前端 JWT token
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
      tokenType: 'access',
    });

    // 获取请求体
    const requestBody = await request.json();
    
    // 根据 sync_type 转换为后端期望的查询参数
    // sync_type: "full" -> sync_recent_only=false, max_products=null (不限制)
    // sync_type: "incremental" (默认) -> sync_recent_only=true, max_products=100
    const syncType = requestBody.sync_type || 'incremental';
    const syncRecentOnly = syncType !== 'full';
    const maxProducts = syncType === 'full' ? '' : '100';
    
    // 构建查询参数
    const queryParams = new URLSearchParams();
    queryParams.set('sync_recent_only', syncRecentOnly.toString());
    if (maxProducts) {
      queryParams.set('max_products', maxProducts);
    }
    const queryString = queryParams.toString();
    
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);

    // 构建后端路径（包含查询参数）
    const backendPath = `/api/v1/products/sync?${queryString}`;
    
    // 构建签名字符串 - POST 请求没有 body 时用空字符串
    const bodyString = '';
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('Sync request parameters', {
      syncType,
      syncRecentOnly,
      maxProducts: maxProducts || 'unlimited',
      backendPath,
    });

    // 获取租户私钥
    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);

    // 生成后端签名
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    logger.info('Generated backend signature', {
      signatureLength: signature.length,
      tenantName,
    });

    // 构建后端请求 URL
    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;

    logger.info('Forwarding request to backend', {
      backendEndpoint: backendUrl,
    });

    // 发送请求到后端 - 使用查询参数而不是 body
    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
        'X-User-ID': userId.toString(),
      },
    });

    const responseTime = Date.now() - startTime;
    logger.info('Backend response received', {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      duration: `${responseTime}ms`,
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('Backend request failed', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('Request completed', {
      method: request.method,
      url: request.url,
      statusCode: 200,
      duration: `${responseTime}ms`,
      tenantName,
      hasData: !!data,
    });

    return NextResponse.json(data);
  } catch (error) {
    const responseTime = Date.now() - startTime;
    logger.error('Request failed', {
      error: String(error),
      errorMessage: error instanceof Error ? error.message : 'Unknown error',
      duration: `${responseTime}ms`,
    });

    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
