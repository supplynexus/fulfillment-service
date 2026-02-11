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
    const printify_product_id = searchParams.get('printify_product_id');
    const limit = searchParams.get('limit') || '100';
    const offset = searchParams.get('offset') || '0';
    const visible_only = searchParams.get('visible_only') || 'false';
    const published_only = searchParams.get('published_only');

    // 构建后端 API 路径
    const backendPath = `/api/v1/printify-products/`;
    
    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendParams = new URLSearchParams();
    if (external_system_id) backendParams.set('external_system_id', external_system_id);
    if (printify_product_id) backendParams.set('printify_product_id', printify_product_id);
    backendParams.set('limit', limit);
    backendParams.set('offset', offset);
    backendParams.set('visible_only', visible_only);
    if (published_only !== null) {
      backendParams.set('published_only', published_only);
    }
    const queryString = backendParams.toString();
    
    // 构建签名字符串 - 必须包含查询参数以匹配后端签名验证逻辑
    const fullPath = queryString
      ? `${backendPath}?${queryString}`
      : backendPath;
    const bodyString = ''; // GET 请求的 body 为空字符串
    const signatureString = `GET${fullPath}${timestamp}${nonce}${tenantName}${bodyString}`;
    
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}${fullPath}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 调用后端 API - fullPath 已经包含查询参数
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
    logger.requestComplete(
      request.method,
      request.url,
      backendResponse.status,
      0
    );

    return NextResponse.json(data);
  } catch (error) {
    logger.error('处理 Printify 商品列表请求失败', { error: String(error) });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
