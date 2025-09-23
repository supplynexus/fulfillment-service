import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.product-detail');

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ product_hashid: string }> }
) {
  const startTime = Date.now();

  try {
    const { product_hashid } = await params;
    
    logger.requestStart(request.method, request.url, {
      product_hashid,
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

    // 获取查询参数
    const { searchParams } = new URL(request.url);
    const include_variants = searchParams.get('include_variants') || 'true';
    const include_dimensions = searchParams.get('include_dimensions') || 'true';
    const include_tags = searchParams.get('include_tags') || 'true';
    const include_mappings = searchParams.get('include_mappings') || 'true';

    // 构建后端请求参数
    const backendParams = new URLSearchParams({
      include_variants,
      include_dimensions,
      include_tags,
      include_mappings,
    });

    // 对于 GET 请求，签名字符串中的 body 应该是空字符串
    const bodyString = '';
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);

    // 构建签名字符串
    const signatureString = `GET/api/v1/products/${product_hashid}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'GET',
      path: `/api/v1/products/${product_hashid}`,
      timestamp,
      nonce,
      tenantName,
      bodyString,
      bodyStringLength: bodyString.length,
      signatureString,
      signatureStringLength: signatureString.length,
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

    logger.info('🔍 前端签名生成完成', {
      signatureLength: signature.length,
      signature: signature.substring(0, 50) + '...',
      tenantName,
    });

    // 构建后端请求 URL
    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/products/${product_hashid}?${backendParams.toString()}`;

    logger.info('Forwarding request to backend', {
      backendEndpoint: backendUrl,
    });

    // 发送请求到后端
    const backendResponse = await fetch(backendUrl, {
      method: 'GET',
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
