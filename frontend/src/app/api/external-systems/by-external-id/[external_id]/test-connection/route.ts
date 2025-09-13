import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger(
  'api.external-systems.test-connection-by-external-id'
);

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ external_id: string }> }
) {
  const startTime = Date.now();

  try {
    // Await params in Next.js 15
    const { external_id } = await params;

    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
      contentType: request.headers.get('content-type'),
      external_id,
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
    } catch (error: any) {
      logger.error('Invalid JWT token', { error: error.message });
      return NextResponse.json(
        { detail: 'Invalid JWT token' },
        { status: 401 }
      );
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Authenticated user', { tenantName, userId });

    // 准备后端请求参数
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = ''; // POST 请求的 body 为空
    const signatureString = `POST/api/v1/external-systems/by-external-id/${external_id}/test-connection${timestamp}${nonce}${tenantName}${bodyString}`;

    // 获取租户私钥
    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);

    // 🔍 调试：打印签名生成信息
    logger.info('🔍 前端签名生成调试信息', {
      method: 'POST',
      path: `/api/v1/external-systems/by-external-id/${external_id}/test-connection`,
      timestamp,
      nonce,
      tenantName,
      bodyString,
      bodyStringLength: bodyString.length,
      signatureString,
      signatureStringLength: signatureString.length,
    });

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
      signature: signature.substring(0, 50) + '...', // 只显示前50个字符
      tenantName,
    });

    // 构建后端请求 URL
    const backendUrl =
      process.env.BACKEND_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';
    const backendEndpoint = `${backendUrl}/api/v1/external-systems/by-external-id/${external_id}/test-connection`;

    logger.info('Forwarding request to backend', {
      backendEndpoint,
      external_id,
    });

    // 发送请求到后端
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
    });

    return NextResponse.json(data);
  } catch (error: any) {
    const responseTime = Date.now() - startTime;
    logger.error('Unexpected error in test connection', {
      error: error.message,
      responseTime,
    });

    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
