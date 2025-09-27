import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.scm-orders.details');

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const startTime = Date.now();
  
  try {
    logger.info('Request started', { 
      method: request.method, 
      url: request.url,
      scm_order_id: params.id
    });

    // 获取前端JWT token
    const frontendToken = request.headers.get('authorization')?.replace('Bearer ', '');
    if (!frontendToken) {
      logger.error('Missing authorization header');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // 验证前端JWT token
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;
    
    logger.info('Frontend token verified', { tenantName, userId });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/scm-orders/${params.id}`;
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}`;
    
    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);
    
    // 调用后端API
    const backendUrl = `${process.env.BACKEND_API_URL || 'http://backend:8000'}${backendPath}`;
    
    logger.info('Calling backend API', { 
      backendUrl, 
      tenantName, 
      userId,
      scm_order_id: params.id
    });

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
      logger.error('Backend API error', { 
        status: backendResponse.status, 
        statusText: backendResponse.statusText,
        error: errorText,
        duration
      });
      
      return NextResponse.json(
        { error: `Backend API error: ${backendResponse.status} ${backendResponse.statusText}` },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    
    logger.requestComplete(request.method, request.url, backendResponse.status, duration);
    
    return NextResponse.json(data);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('Request failed', { 
      error: error.message, 
      stack: error.stack,
      duration
    });
    
    return NextResponse.json(
      { error: 'Internal server error', detail: error.message },
      { status: 500 }
    );
  }
}
