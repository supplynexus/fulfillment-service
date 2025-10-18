import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.create-from-external');

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
    });

    // 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('❌ 缺少认证头');
      return NextResponse.json(
        { error: 'Missing authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      logger.error('❌ JWT token 验证失败', { error: String(error) });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;

    if (!tenantName || !userId) {
      logger.warn('❌ JWT token 缺少 tenant_name 或 user_id');
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    // 获取请求体
    const requestBody = await request.json();
    const { external_product_id } = requestBody;

    if (!external_product_id) {
      logger.error('❌ 缺少外部商品ID');
      return NextResponse.json(
        { error: 'External product ID is required' },
        { status: 400 }
      );
    }

    // 构建后端请求URL
    const backendPath = `/api/v1/products/create-from-external`;
    const bodyString = JSON.stringify(requestBody);
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'POST',
      path: backendPath,
      timestamp,
      nonce,
      tenantName,
      signatureString,
      signatureStringLength: signatureString.length,
    });

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
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

    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;

    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-User-ID': userId.toString(),
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
      },
      body: bodyString,
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();
      logger.error('❌ 后端 API 调用失败', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorData,
      });
      return NextResponse.json(errorData, { status: backendResponse.status });
    }

    const data = await backendResponse.json();
    logger.info('✅ 从外部商品创建核心商品成功', {
      external_product_id,
      core_product_id: data.id_hashid,
      duration: Date.now() - startTime,
    });
    return NextResponse.json(data);
  } catch (error: any) {
    logger.error('❌ 处理请求失败', {
      error: error.message,
      stack: error.stack,
    });
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }
}
