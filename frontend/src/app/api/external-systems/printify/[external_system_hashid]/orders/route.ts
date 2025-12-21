import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.printify.orders');

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ external_system_hashid: string }> }
) {
  const startTime = Date.now();
  const { external_system_hashid } = await params;

  try {
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const token = authHeader.split(' ')[1];
    let decodedToken;
    try {
      decodedToken = await jwtUtilsServer.verifyToken(token);
    } catch (error) {
      logger.error('Invalid frontend token', { error: String(error) });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Frontend JWT verified successfully', {
      userId,
      tenantName,
      externalSystemHashid: external_system_hashid,
      tokenType: 'access',
    });

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const queryString = searchParams.toString();

    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    // Build full path with query parameters to match backend signature verification
    const backendPath = queryString
      ? `/api/v1/external-systems/printify/${external_system_hashid}/orders?${queryString}`
      : `/api/v1/external-systems/printify/${external_system_hashid}/orders`;
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);

    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    logger.info('Backend signature generated', {
      signatureLength: signature.length,
      tenantName,
      externalSystemHashid: external_system_hashid,
    });

    const backendApiUrl = process.env.BACKEND_API_URL || 'http://backend:8000';
    const backendEndpoint = `${backendApiUrl}${backendPath}`;

    logger.info('Forwarding request to backend', { backendEndpoint });

    const backendResponse = await fetch(backendEndpoint, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
        'X-User-ID': userId,
      },
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();
      logger.error('Backend request failed', {
        status: backendResponse.status,
        error: JSON.stringify(errorData),
        duration: Date.now() - startTime,
      });
      return NextResponse.json(errorData, {
        status: backendResponse.status,
      });
    }

    const data = await backendResponse.json();
    logger.info('Backend request completed successfully', {
      success: true,
      duration: Date.now() - startTime,
      ordersCount: data.orders?.length,
    });

    return NextResponse.json(data);
  } catch (error: any) {
    logger.error('Error processing request', {
      error: String(error),
      errorMessage: error.message,
      errorStack: error.stack,
      duration: Date.now() - startTime,
    });
    return NextResponse.json(
      { detail: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
