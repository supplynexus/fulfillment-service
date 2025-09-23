import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';

const logger = createLogger('api.shopify-order-details');

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ orderId: string }> }
) {
  try {
    const { orderId } = await params;
    const { searchParams } = new URL(request.url);
    const shopId = searchParams.get('shop_id');

    if (!shopId) {
      return NextResponse.json(
        { error: 'Missing shop_id parameter' },
        { status: 400 }
      );
    }

    logger.requestStart('GET', `/api/external-systems/shopify/orders/${orderId}`);

    // Get authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader) {
      logger.error('Missing authorization header');
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      );
    }

    // Decode JWT token to get tenant information
    const token = authHeader.replace('Bearer ', '');
    const decodedToken = jwtUtilsServer.verifyToken(token);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('Authenticated user', { tenantName, userId });

    // Generate signature for backend request
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const backendPath = `/api/v1/external-systems/shopify/${shopId}/orders/${orderId}`;
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

    // Call backend API
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}${backendPath}`;
    
    logger.info('Forwarding request to backend', { backendUrl });

    const response = await fetch(backendUrl, {
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

    if (!response.ok) {
      const errorData = await response.json();
      logger.error('Backend API error', { 
        status: response.status, 
        error: errorData 
      });
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch order details' },
        { status: response.status }
      );
    }

    const data = await response.json();
    
    logger.requestComplete('GET', `/api/external-systems/shopify/orders/${orderId}`, response.status, 0);
    
    return NextResponse.json(data);

  } catch (error) {
    logger.error('Error fetching Shopify order details', { 
      error: error instanceof Error ? error.message : 'Unknown error' 
    });
    
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
