import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.external-systems.id');

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const startTime = Date.now();

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
      tokenType: 'access',
    });

    // Extract external system ID from URL params
    const { id: externalSystemId } = await params;

    if (!externalSystemId || isNaN(Number(externalSystemId))) {
      logger.error('Invalid external system ID', { externalSystemId });
      return NextResponse.json(
        { detail: 'Invalid external system ID' },
        { status: 400 }
      );
    }

    const body = await request.json();
    logger.info('Processing external system update request', {
      tenantName,
      externalSystemId,
      systemType: body.system_type,
      name: body.name,
      externalId: body.external_system_id,
    });

    const bodyString = JSON.stringify(body);
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `PUT/api/v1/external-systems/${externalSystemId}${timestamp}${nonce}${tenantName}${bodyString}`;

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
      externalSystemId,
    });

    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/external-systems/${externalSystemId}`;

    const backendResponse = await fetch(backendUrl, {
      method: 'PUT',
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

    const duration = Date.now() - startTime;

    if (!backendResponse.ok) {
      let errorData;
      try {
        errorData = await backendResponse.json();
      } catch {
        errorData = await backendResponse.text();
      }

      logger.error('Backend request failed', {
        status: backendResponse.status,
        error: errorData,
        duration,
        externalSystemId,
      });

      // Pass through the backend error message
      return NextResponse.json(errorData, { status: backendResponse.status });
    }

    const data = await backendResponse.json();
    logger.info('External system update request completed successfully', {
      success: true,
      duration,
      systemId: data.id,
      systemType: data.system_type,
    });

    return NextResponse.json(data);
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error('Error in external system update API route', {
      error: String(error),
      duration,
    });
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}