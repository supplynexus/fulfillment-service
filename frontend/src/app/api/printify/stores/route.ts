import { NextRequest, NextResponse } from 'next/server';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { createLogger } from '@/lib/logger';

const logger = createLogger('api.printify-stores');

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.requestStart(request.method, request.url);

    // 获取前端 JWT token
    const frontendToken = request.headers
      .get('authorization')
      ?.replace('Bearer ', '');
    if (!frontendToken) {
      logger.error('缺少前端 JWT token');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // 验证前端 JWT token
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('前端 JWT 验证成功', { tenantName, userId });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = '/api/v1/printify/stores';
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 调用后端 API
    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;
    logger.info('调用后端 API', { url: backendUrl });

    const backendResponse = await fetch(backendUrl, {
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

    const responseData = await backendResponse.json();
    const duration = Date.now() - startTime;

    if (backendResponse.ok) {
      logger.requestComplete(
        request.method,
        request.url,
        backendResponse.status,
        duration
      );
      return NextResponse.json(responseData);
    } else {
      logger.error('后端 API 调用失败', {
        status: backendResponse.status,
        error: responseData,
      });
      return NextResponse.json(
        { error: 'Failed to fetch Printify stores' },
        { status: backendResponse.status }
      );
    }
  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('获取 Printify 店铺列表失败', {
      error: error.message,
      duration,
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
