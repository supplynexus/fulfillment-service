import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.external-systems.shopify.orders');

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ external_system_hashid: string }> }
) {
  const startTime = Date.now();
  const { external_system_hashid } = await params;
  
  try {
    logger.info('Request started', { 
      method: request.method, 
      url: request.url,
      external_system_hashid
    });

    const authorization = request.headers.get('authorization');
    if (!authorization) {
      logger.error('Missing authorization header');
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      );
    }

    // Verify JWT token and get user info
    const token = authorization.replace('Bearer ', '');
    const decodedToken = jwtUtilsServer.verifyToken(token);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('Authenticated user', { tenantName, userId });

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const page = searchParams.get('page') || '1';
    const limit = searchParams.get('limit') || '20';
    const search = searchParams.get('search') || '';
    const sortBy = searchParams.get('sort_by') || 'created_at';
    const sortOrder = searchParams.get('sort_order') || 'desc';
    const status = searchParams.get('status') || '';
    const financialStatus = searchParams.get('financial_status') || '';
    const fulfillmentStatus = searchParams.get('fulfillment_status') || '';

    // Generate signature for backend request
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const backendPath = `/api/v1/external-systems/shopify/${external_system_hashid}/orders`;
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'GET',
      path: backendPath,
      timestamp,
      nonce,
      tenantName,
      bodyString,
      bodyStringLength: bodyString.length,
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

    const backendUrl = `${process.env.BACKEND_API_URL || 'http://localhost:8000'}${backendPath}?page=${page}&limit=${limit}&search=${encodeURIComponent(search)}&sort_by=${sortBy}&sort_order=${sortOrder}&status=${status}&financial_status=${financialStatus}&fulfillment_status=${fulfillmentStatus}`;
    
    logger.info('Forwarding request to backend', { backendUrl });

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

    const responseData = await backendResponse.json();

    if (!backendResponse.ok) {
      logger.error('Backend request failed', {
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
    logger.info('Request completed', { 
      method: request.method, 
      url: request.url,
      status: 200,
      duration: `${duration}ms`
    });
    
    return NextResponse.json(responseData);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('API request failed', { 
      error: error.message,
      duration: `${duration}ms`
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}