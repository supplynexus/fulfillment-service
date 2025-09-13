import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.external-systems.shopify.sync-orders');

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ shop_id: string }> }
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
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error: any) {
      logger.error('Invalid JWT token', { error: error.message });
      return NextResponse.json(
        { detail: 'Invalid JWT token' },
        { status: 401 }
      );
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Authenticated user', { tenantName, userId });

    const { shop_id } = await params;
    logger.info('Request data received', { shop_id });

    // Generate signature for backend request
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `POST/api/v1/external-systems/shopify/${shop_id}/sync-orders${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);

    logger.info('🔍 前端签名生成调试信息', {
      method: 'POST',
      path: `/api/v1/external-systems/shopify/${shop_id}/sync-orders`,
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
      process.env.BACKEND_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';
    const backendEndpoint = `${backendUrl}/api/v1/external-systems/shopify/${shop_id}/sync-orders`;

    logger.info('Forwarding request to backend', {
      backendEndpoint,
      shop_id,
    });

    const backendResponse = await fetch(backendEndpoint, {
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
      responseTime,
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
    logger.info('Request completed successfully', {
      responseTime,
      success: data.success,
      orders_synced: data.orders_synced,
      orders_updated: data.orders_updated,
    });

    return NextResponse.json(data);
  } catch (error: any) {
    const responseTime = Date.now() - startTime;
    logger.error('Unexpected error in sync orders', {
      error: error.message,
      responseTime,
    });
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
