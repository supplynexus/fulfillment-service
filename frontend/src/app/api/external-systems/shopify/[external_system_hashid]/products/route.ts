import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.external-systems.shopify.products');

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ external_system_hashid: string }> }
) {
  const startTime = Date.now();

  try {
    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
      contentType: request.headers.get('content-type'),
    });

    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('Authenticated user', { tenantName, userId });

    const { external_system_hashid } = await params;
    logger.info('Request data received', { external_system_hashid });

    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `GET/api/v1/external-systems/shopify/${external_system_hashid}/products${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);

    logger.info('🔍 前端签名生成调试信息', {
      method: 'GET',
      path: `/api/v1/external-systems/shopify/${external_system_hashid}/products`,
      timestamp,
      nonce,
      tenantName,
      signatureString,
      signatureStringLength: signatureString.length,
    });

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

    const backendUrl =
      `${process.env.BACKEND_API_URL}/api/v1/external-systems/shopify/${external_system_hashid}/products`;

    logger.info('Forwarding request to backend', {
      backendEndpoint: backendUrl,
      external_system_hashid,
    });

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
    logger.info('Backend response received', {
      status: response.status,
      responseTime,
    });

    if (!response.ok) {
      const errorData = await response.json();
      logger.error('Backend request failed', {
        status: response.status,
        statusText: response.statusText,
        error: errorData,
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: response.status }
      );
    }

    const data = await response.json();

    logger.requestComplete(request.method, request.url, response.status, responseTime);

    return NextResponse.json(data);
  } catch (error) {
    const responseTime = Date.now() - startTime;
    logger.error('Error in Shopify products API', {
      error: error instanceof Error ? error.message : 'Unknown error',
      responseTime,
    });

    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}