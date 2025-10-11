import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.external-products');

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
    });

    // 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('❌ 缺少认证头');
      return NextResponse.json({ error: 'Missing authorization header' }, { status: 401 });
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

    logger.info('✅ 前端认证成功', { tenantName, userId });
    
    if (!tenantName || !userId) {
      logger.error('❌ JWT token 缺少 tenant_name 或 user_id');
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    // 获取查询参数
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '10');
    const skip = (page - 1) * limit;

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/products/external-products/`;
    const queryString = `skip=${skip}&limit=${limit}`;
    const fullPath = `${backendPath}?${queryString}`;
    // 签名字符串不包含查询参数，只包含路径
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}`;

    // 🔍 调试：打印签名生成信息
    logger.info('🔍 前端签名生成调试信息', {
      method: 'GET',
      path: backendPath,
      timestamp,
      nonce,
      tenantName,
      signatureString,
      signatureStringLength: signatureString.length,
    });

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);

    logger.info('🔍 前端签名生成完成', {
      signatureLength: signature.length,
      signature: signature.substring(0, 50) + '...',
      tenantName,
    });

    // 调用后端 API
    const backendUrl = `${process.env.BACKEND_API_URL}${fullPath}`;
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

    const duration = Date.now() - startTime;

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('❌ 后端API调用失败', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
        duration,
      });
      return NextResponse.json(
        { error: `Backend API error: ${backendResponse.status}` },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.requestComplete(request.method, request.url, backendResponse.status, duration);

    return NextResponse.json(data);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('❌ 外部商品API调用失败', {
      error: error.message,
      duration,
    });
    return NextResponse.json(
      { error: 'Failed to fetch external products' },
      { status: 500 }
    );
  }
}

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
      return NextResponse.json({ error: 'Missing authorization header' }, { status: 401 });
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
      logger.error('❌ JWT token 缺少 tenant_name 或 user_id');
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    // 获取请求体
    const requestBody = await request.json();
    logger.info('🔍 开始处理外部商品同步请求', { 
      tenantName, 
      userId,
      externalProductId: requestBody.external_product_id 
    });

    // 构建后端请求URL
    const backendPath = `/api/v1/products/external-products/`;
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
    
    logger.info('Forwarding request to backend', { backendUrl });

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

    const responseData = await backendResponse.json();

    if (!backendResponse.ok) {
      logger.error('❌ 后端 API 调用失败', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: responseData
      });
      
      return NextResponse.json(
        { error: responseData.detail || 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const duration = Date.now() - startTime;
    logger.info('✅ 外部商品同步成功', {
      externalProductId: requestBody.external_product_id,
      duration: `${duration}ms`
    });
    
    return NextResponse.json(responseData);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('❌ 处理外部商品同步请求失败', { 
      error: error.message,
      duration: `${duration}ms`
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}