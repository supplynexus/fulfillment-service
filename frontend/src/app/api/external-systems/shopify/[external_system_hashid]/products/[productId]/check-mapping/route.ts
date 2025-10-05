import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.shopify-check-mapping');

export async function GET(
  request: NextRequest,
  {
    params,
  }: {
    params: Promise<{ external_system_hashid: string; productId: string }>;
  }
) {
  const startTime = Date.now();

  try {
    const { external_system_hashid, productId } = await params;

    logger.requestStart(request.method, request.url, {
      external_system_hashid,
      productId,
      userAgent: request.headers.get('user-agent'),
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

    // 对于 GET 请求，body 为空字符串
    const bodyString = '';
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);

    // 构建后端路径
    const backendPath = `/api/v1/external-systems/shopify/${external_system_hashid}/products/${productId}/check-mapping`;

    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'GET',
      path: backendPath,
      timestamp,
      nonce,
      tenantName,
      bodyString,
      bodyStringLength: bodyString.length,
      signatureString,
      signatureStringLength: signatureString.length,
    });

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    logger.info('🔍 前端签名生成完成', {
      signatureLength: signature.length,
      signature: signature.substring(0, 50) + '...',
      tenantName,
    });

    // 调用后端 API
    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;

    logger.info('Forwarding request to backend', { backendUrl });

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-User-ID': userId,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
      },
    });

    const responseTime = Date.now() - startTime;

    if (!response.ok) {
      const errorData = await response.json();
      logger.error('Backend API error', {
        status: response.status,
        error: errorData,
        responseTime,
      });
      return NextResponse.json(
        { error: errorData.detail || 'Failed to check product mapping' },
        { status: response.status }
      );
    }

    const data = await response.json();

    logger.requestComplete(
      'GET',
      `/api/external-systems/shopify/${external_system_hashid}/products/${productId}/check-mapping`,
      response.status,
      responseTime
    );

    return NextResponse.json(data);
  } catch (error) {
    const responseTime = Date.now() - startTime;
    logger.error('Error checking Shopify product mapping', {
      error: error instanceof Error ? error.message : 'Unknown error',
      responseTime,
    });

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
