import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.product-detail');

export async function PUT(
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

    // 获取请求体
    const requestBody = await request.json();
    const bodyString = JSON.stringify(requestBody);

    logger.info('🔍 前端更新商品请求体', {
      product_hashid,
      requestBodyKeys: Object.keys(requestBody),
      bodyStringLength: bodyString.length,
    });

    // 生成签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);

    // 构建签名字符串
    const signatureString = `PUT/api/v1/products/${product_hashid}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'PUT',
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
    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/products/${product_hashid}`;

    logger.info('Forwarding PUT request to backend', {
      backendEndpoint: backendUrl,
    });

    // 发送请求到后端
    const backendResponse = await fetch(backendUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
        'X-User-ID': userId.toString(),
      },
      body: bodyString,
    });

    const responseTime = Date.now() - startTime;
    logger.info('Backend PUT response received', {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      duration: `${responseTime}ms`,
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('Backend PUT request failed', {
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
    logger.info('PUT request completed', {
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
    logger.error('PUT request failed', {
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

    // 构建签名字符串 - 必须包含查询参数以匹配后端签名验证逻辑
    const queryString = backendParams.toString();
    const backendPath = queryString
      ? `/api/v1/products/${product_hashid}?${queryString}`
      : `/api/v1/products/${product_hashid}`;
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'GET',
      path: backendPath,
      queryString,
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

    // 构建后端请求 URL - backendPath 已经包含查询参数
    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;

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

export async function DELETE(
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

    // 对于 DELETE 请求，签名字符串中的 body 应该是空字符串
    const bodyString = '';
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);

    // 构建签名字符串
    const signatureString = `DELETE/api/v1/products/${product_hashid}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端删除商品签名生成调试信息', {
      method: 'DELETE',
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

    logger.info('🔍 前端删除商品签名生成完成', {
      signatureLength: signature.length,
      signature: signature.substring(0, 50) + '...',
      tenantName,
    });

    // 构建后端请求 URL
    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/products/${product_hashid}`;

    logger.info('Forwarding DELETE request to backend', {
      backendEndpoint: backendUrl,
    });

    // 发送请求到后端
    const backendResponse = await fetch(backendUrl, {
      method: 'DELETE',
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
    logger.info('Backend DELETE response received', {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      duration: `${responseTime}ms`,
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      let detail = 'Backend request failed';
      try {
        const parsed = JSON.parse(errorText);
        if (typeof parsed?.detail === 'string') detail = parsed.detail;
      } catch {
        if (errorText) detail = errorText;
      }
      logger.error('Backend DELETE request failed', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });
      return NextResponse.json(
        { detail },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('DELETE request completed', {
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
    logger.error('DELETE request failed', {
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
