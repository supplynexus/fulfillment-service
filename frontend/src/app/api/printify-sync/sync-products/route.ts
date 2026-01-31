import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';

const logger = createLogger('api.printify-sync-products');

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  logger.requestStart(request.method, request.url);

  try {
    // 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const frontendToken = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('处理 Printify 商品同步请求', { tenantName, userId });

    // 获取请求体
    const requestBody = await request.json();
    const { external_system_id_hashid } = requestBody;

    if (!external_system_id_hashid) {
      return NextResponse.json(
        { error: 'external_system_id_hashid is required' },
        { status: 400 }
      );
    }

    // 构建后端 API 路径
    const backendPath = `/api/v1/printify-sync/sync-products`;
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${backendPath}`;

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = JSON.stringify(requestBody);
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 调用后端 API
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
      body: bodyString,
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('后端 API 调用失败', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });
      return NextResponse.json(
        { error: 'Backend API call failed', details: errorText },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    const duration = (Date.now() - startTime) / 1000;
    logger.requestComplete(
      request.method,
      request.url,
      backendResponse.status,
      duration
    );

    return NextResponse.json(data);
  } catch (error) {
    logger.error('处理 Printify 商品同步请求失败', { error: String(error) });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
