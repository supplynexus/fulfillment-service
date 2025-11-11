import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.scm-orders.batch-update-shopify-fulfillment');

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  try {
    logger.requestStart(request.method, request.url);
    
    // 1. 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('❌ 缺少或无效的 Authorization 头');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const frontendToken = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;
    
    logger.info('✅ 前端 JWT token 验证成功', { tenantName, userId });

    // 2. 解析请求体
    const requestBody = await request.json();
    const { scm_order_hashids } = requestBody;
    
    if (!scm_order_hashids || !Array.isArray(scm_order_hashids)) {
      logger.error('❌ 缺少或无效的 scm_order_hashids 参数');
      return NextResponse.json({ error: 'Invalid scm_order_hashids' }, { status: 400 });
    }

    logger.info('📦 批量更新 Shopify fulfillment 请求', { 
      count: scm_order_hashids.length,
      hashids: scm_order_hashids 
    });

    // 3. 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = JSON.stringify(requestBody);
    const backendPath = '/api/v1/scm-orders/batch-update-shopify-fulfillment';
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
    const duration = Date.now() - startTime;
    
    if (!backendResponse.ok) {
      logger.error('❌ 后端 API 调用失败', { 
        status: backendResponse.status, 
        response: responseData,
        duration: `${duration}ms`
      });
      return NextResponse.json(
        { error: responseData.detail || 'Backend API error' }, 
        { status: backendResponse.status }
      );
    }

    logger.requestComplete(request.method, request.url, backendResponse.status, duration);
    logger.info('✅ 批量更新 Shopify fulfillment 成功', { 
      successCount: responseData.results?.success?.length || 0,
      failedCount: responseData.results?.failed?.length || 0
    });

    return NextResponse.json(responseData);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('❌ 批量更新 Shopify fulfillment 失败', { 
      error: error.message,
      duration: `${duration}ms`
    });
    logger.error('   异常堆栈', { stack: error.stack });
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    );
  }
}
