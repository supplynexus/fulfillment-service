import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.orders.batch-update-shopify-status');

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  try {
    logger.requestStart(request.method, request.url);
    console.log('🔍 前端API路由开始处理请求');
    
    // 1. 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('❌ 缺少或无效的 Authorization 头');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const frontendToken = authHeader.substring(7);
    logger.info('🔍 开始验证JWT token', { 
      tokenLength: frontendToken.length,
      tokenPrefix: frontendToken.substring(0, 20) + '...'
    });
    
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
      logger.info('✅ JWT token验证成功', { decodedToken });
    } catch (jwtError: any) {
      logger.error('❌ JWT token验证失败', { 
        error: jwtError.message,
        errorType: typeof jwtError,
        errorName: jwtError.name
      });
      throw jwtError;
    }
    
    const { tenant_name: tenantName, sub: userId } = decodedToken;
    
    logger.info('✅ 前端 JWT token 验证成功', { tenantName, userId });

    // 2. 解析请求体
    const requestBody = await request.json();
    const { order_ids } = requestBody;
    
    if (!order_ids || !Array.isArray(order_ids)) {
      logger.error('❌ 缺少或无效的 order_ids 参数');
      return NextResponse.json({ error: 'Invalid order_ids' }, { status: 400 });
    }

    logger.info('📦 批量更新 Shopify 订单状态请求', { 
      count: order_ids.length,
      hashids: order_ids 
    });

    // 3. 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = JSON.stringify(requestBody);
    const backendPath = '/api/v1/orders/batch-update-shopify-status';
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;
    
    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);
    
    logger.info('✅ 后端签名生成成功', { timestamp, nonce });

    // 4. 调用后端 API
    const backendUrl = `${process.env.BACKEND_API_URL || 'http://localhost:8000'}${backendPath}`;
    
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

    const responseData = await backendResponse.json();
    
    if (!backendResponse.ok) {
      logger.error('❌ 后端 API 调用失败', { 
        status: backendResponse.status, 
        response: responseData 
      });
      return NextResponse.json(
        { error: responseData.detail || 'Backend API error' }, 
        { status: backendResponse.status }
      );
    }

    const duration = (Date.now() - startTime) / 1000;
    logger.requestComplete(request.method, request.url, backendResponse.status, duration);
    logger.info('✅ 批量更新 Shopify 订单状态成功', { 
      successCount: responseData.results?.success?.length || 0,
      failedCount: responseData.results?.failed?.length || 0
    });

    return NextResponse.json(responseData);

  } catch (error: any) {
    logger.error('❌ 批量更新 Shopify 订单状态失败', { 
      error: error.message,
      errorType: typeof error,
      errorName: error.name,
      errorStack: error.stack,
      errorString: String(error)
    });
    return NextResponse.json(
      { 
        error: 'Internal server error',
        details: error.message,
        type: typeof error
      }, 
      { status: 500 }
    );
  }
}
