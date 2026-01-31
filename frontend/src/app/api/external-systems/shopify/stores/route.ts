import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.external-systems.shopify.stores');

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.info('Request started', {
      method: request.method,
      url: request.url,
    });

    // Get authorization header from the request
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

    // Generate signature for backend request
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const backendPath = '/api/v1/shopify/stores';
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // Forward the request to the backend
    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;

    logger.info('Forwarding request to backend', { backendUrl });

    const backendResponse = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: authorization, // Add Authorization header for backend
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
        error: responseData,
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
      duration: `${duration}ms`,
    });

    return NextResponse.json(responseData);
  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('API request failed', {
      error: error.message,
      duration: `${duration}ms`,
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
