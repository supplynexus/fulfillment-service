import { NextRequest, NextResponse } from 'next/server';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { createLogger } from '@/lib/logger';

const logger = createLogger('api.orders.sync');

export async function POST(request: NextRequest) {
  logger.requestStart(request.method, request.url);
  
  try {
    // 1. 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const frontendToken = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('处理订单同步请求', { tenantName, userId });

    // 2. 获取请求体
    const requestBody = await request.json();
    logger.info('同步参数', requestBody);

    // 3. 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = JSON.stringify(requestBody);
    const backendPath = '/api/v1/orders/sync';
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);

    // 4. 调用后端 API
    const backendUrl = `${process.env.BACKEND_API_URL || 'http://backend:8000'}${backendPath}`;
    logger.info('调用后端API', { url: backendUrl });

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
      logger.error('后端API调用失败', { 
        status: backendResponse.status, 
        error: responseData 
      });
      return NextResponse.json(responseData, { status: backendResponse.status });
    }

    logger.requestComplete(request.method, request.url, backendResponse.status, Date.now());
    return NextResponse.json(responseData);

  } catch (error) {
    logger.error('订单同步失败', { error: error instanceof Error ? error.message : String(error) });
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    );
  }
}
