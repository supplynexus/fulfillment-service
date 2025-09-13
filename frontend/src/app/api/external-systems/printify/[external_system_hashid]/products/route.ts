import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.printify.products');

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

    const frontendToken = authHeader.substring(7);
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
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

    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `GET/api/v1/external-systems/printify/${external_system_hashid}/products${timestamp}${nonce}${tenantName}`;

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

    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/external-systems/printify/${external_system_hashid}/products`;

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
      const errorData = await backendResponse.text();
      logger.error('Backend request failed', {
        status: backendResponse.status,
        error: errorData,
        duration,
        externalSystemHashid: external_system_hashid,
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('Printify products request completed successfully', {
      success: data.success,
      duration,
      externalSystemHashid: external_system_hashid,
      productsCount: data.products?.length || 0,
    });

    return NextResponse.json(data);
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error('Error in Printify products API route', {
      error: String(error),
      duration,
      externalSystemHashid: external_system_hashid,
    });
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
