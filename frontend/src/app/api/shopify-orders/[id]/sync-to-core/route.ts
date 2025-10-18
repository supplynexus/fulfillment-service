import { NextRequest, NextResponse } from 'next/server';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { createLogger } from '@/lib/logger';

const logger = createLogger('api.shopify-orders.sync-to-core');

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const startTime = Date.now();

  try {
    const { id } = await params;
    logger.requestStart('POST', `/api/shopify-orders/${id}/sync-to-core`);

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
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('JWT token verified', { tenantName, userId });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/shopify-orders/${id}/sync-to-core`;
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 调用后端 API
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8000'}${backendPath}`;
    logger.info('Calling backend API', { backendUrl });

    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-User-ID': userId,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
      },
    });

    const duration = Date.now() - startTime;
    logger.requestComplete(
      'POST',
      `/api/shopify-orders/${id}/sync-to-core`,
      backendResponse.status,
      duration
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();
      logger.error('Backend API error', {
        status: backendResponse.status,
        error: errorData,
      });
      return NextResponse.json(
        { detail: errorData.detail || 'Backend API error' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('Sync to core order successful', {
      orderId: id,
      coreOrderId: data.core_order_id,
      itemsCount: data.items_count,
    });

    return NextResponse.json(data);
  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('Sync to core order failed', {
      error: error.message,
      duration,
    });

    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
