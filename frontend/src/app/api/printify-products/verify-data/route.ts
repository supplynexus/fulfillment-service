import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';

const logger = createLogger('api.printify-products-verify');

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const frontendToken = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    const { searchParams } = new URL(request.url);
    const external_system_id_hashid = searchParams.get('external_system_id_hashid');
    const limit = searchParams.get('limit') || '2';

    if (!external_system_id_hashid) {
      return NextResponse.json(
        { error: 'external_system_id_hashid is required' },
        { status: 400 }
      );
    }

    const queryString = `external_system_id_hashid=${encodeURIComponent(external_system_id_hashid)}&limit=${limit}`;
    const backendPath = `/api/v1/printify-products/verify-data?${queryString}`;
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${backendPath}`;

    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

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

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('Backend verify-data failed', {
        status: backendResponse.status,
        error: errorText,
      });
      return NextResponse.json(
        { error: 'Backend API call failed', details: errorText },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    logger.error('printify-products verify-data failed', { error: String(error) });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
