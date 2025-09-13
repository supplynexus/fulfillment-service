import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.orders.create-shipping-label');

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const startTime = Date.now();
  
  try {
    // 验证 Authorization header
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

    const { id } = await params;
    logger.info('Processing create shipping label request', { orderId: id, tenantName });

    // 构建签名字符串
    const bodyString = ''; // POST 请求的 body 为空
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `POST/api/v1/orders/${id}/create-shipping-label${timestamp}${nonce}${tenantName}${bodyString}`;

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

    logger.info('Backend signature generated', {
      signatureLength: signature.length,
      tenantName,
    });

    // 构建后端请求 URL
    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/orders/${id}/create-shipping-label`;

    // 转发请求到后端
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
    
    if (!backendResponse.ok) {
      const errorData = await backendResponse.text();
      logger.error('Backend request failed', {
        status: backendResponse.status,
        error: errorData,
        duration,
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('Create shipping label request completed successfully', {
      orderId: id,
      duration,
    });

    return NextResponse.json(data);
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error('Error in create shipping label API route', {
      error: String(error),
      duration,
    });
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
