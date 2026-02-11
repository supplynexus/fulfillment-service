import { NextRequest, NextResponse } from 'next/server';

import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { createLogger } from '@/lib/logger';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.printify-products-local-sync-status');

export async function POST(
  request: NextRequest,
  {
    params,
  }: {
    params: Promise<{ external_system_hashid: string }>;
  }
) {
  const startTime = Date.now();
  try {
    const { external_system_hashid } = await params;
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    const body = await request.json();
    const bodyString = JSON.stringify(body || {});
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/external-systems/printify/${external_system_hashid}/products/local-sync-status`;
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

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

    if (!response.ok) {
      const errorData = await response.json();
      logger.error('Backend request failed', {
        status: response.status,
        error: errorData,
      });
      return NextResponse.json(
        { error: errorData.detail || 'Failed to compare local sync status' },
        { status: response.status }
      );
    }

    const data = await response.json();
    logger.requestComplete(
      'POST',
      `/api/external-systems/printify/${external_system_hashid}/products/local-sync-status`,
      200,
      Date.now() - startTime
    );
    return NextResponse.json(data);
  } catch (error) {
    logger.error('Error in local-sync-status route', {
      error: error instanceof Error ? error.message : String(error),
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
