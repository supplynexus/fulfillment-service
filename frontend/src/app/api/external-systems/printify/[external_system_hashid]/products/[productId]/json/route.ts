import { NextRequest, NextResponse } from 'next/server';

import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { createLogger } from '@/lib/logger';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.printify-product-json');

export async function GET(
  request: NextRequest,
  {
    params,
  }: {
    params: Promise<{ external_system_hashid: string; productId: string }>;
  }
) {
  const startTime = Date.now();
  try {
    const { external_system_hashid, productId } = await params;

    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
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
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const backendPath = `/api/v1/external-systems/printify/${external_system_hashid}/products/${productId}/json`;
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;
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

    const duration = Date.now() - startTime;
    if (!response.ok) {
      const errorData = await response.json();
      logger.error('Backend API error', {
        status: response.status,
        error: errorData,
        duration,
      });
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch Printify product JSON' },
        { status: response.status }
      );
    }

    const data = await response.json();
    logger.requestComplete(
      'GET',
      `/api/external-systems/printify/${external_system_hashid}/products/${productId}/json`,
      response.status,
      duration
    );
    return NextResponse.json(data);
  } catch (error) {
    logger.error('Error fetching Printify product JSON', {
      error: error instanceof Error ? error.message : 'Unknown error',
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
