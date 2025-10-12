import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';

const logger = createLogger('api.printify-products');

export async function GET(request: NextRequest) {
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

    logger.info('处理 Printify 商品列表请求', { tenantName, userId });

    // 获取查询参数
    const { searchParams } = new URL(request.url);
    const external_system_id = searchParams.get('external_system_id');
    const limit = searchParams.get('limit') || '100';
    const offset = searchParams.get('offset') || '0';
    const visible_only = searchParams.get('visible_only') || 'false';

    // 构建后端 API 路径
    const backendPath = `/api/v1/printify-products/`;
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}${backendPath}`;

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const queryString = `external_system_id=${external_system_id}&limit=${limit}&offset=${offset}&visible_only=${visible_only}`;
    // GET 请求的 body 为空字符串
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);

    // 调用后端 API
    const backendResponse = await fetch(`${backendUrl}?${queryString}`, {
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

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('后端 API 调用失败', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });
      return NextResponse.json(
        { error: 'Backend API call failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.requestComplete(request.method, request.url, backendResponse.status, 0);

    return NextResponse.json(data);
  } catch (error) {
    logger.error('处理 Printify 商品列表请求失败', { error: String(error) });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
