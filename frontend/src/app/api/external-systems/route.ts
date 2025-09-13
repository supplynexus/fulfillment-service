import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.external-systems');

export async function GET(request: NextRequest) {
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

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const systemType = searchParams.get('system_type');
    const activeOnly = searchParams.get('active_only') !== 'false';

    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `GET/api/v1/external-systems/${timestamp}${nonce}${tenantName}`;

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
      systemType,
      activeOnly,
    });

    // Build query string
    const queryParams = new URLSearchParams();
    if (systemType) queryParams.append('system_type', systemType);
    if (!activeOnly) queryParams.append('active_only', 'false');

    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/external-systems${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

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
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    
    // Debug: Log the first system to check if id_hashid is present
    if (data.external_systems && data.external_systems.length > 0) {
      const firstSystem = data.external_systems[0];
      logger.info('Debug: First system data', {
        id: firstSystem.id,
        id_hashid: firstSystem.id_hashid,
        name: firstSystem.name,
        system_type: firstSystem.system_type,
        hasIdHashid: !!firstSystem.id_hashid
      });
    }
    
    logger.info('External systems fetch request completed successfully', {
      success: true,
      duration,
      systemsCount: data.external_systems?.length || 0,
    });

    return NextResponse.json(data);
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error('Error in external systems fetch API route', {
      error: String(error),
      duration,
    });
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
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

    const body = await request.json();
    logger.info('Processing external system creation request', { 
      tenantName,
      systemType: body.system_type,
      name: body.name,
      externalId: body.external_system_id
    });

    const bodyString = JSON.stringify(body);
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `POST/api/v1/external-systems/${timestamp}${nonce}${tenantName}${bodyString}`;

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
    });

    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/external-systems`;

    const backendResponse = await fetch(backendUrl, {
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

    const duration = Date.now() - startTime;

    if (!backendResponse.ok) {
      const errorData = await backendResponse.text();
      logger.error('Backend request failed', {
        status: backendResponse.status,
        error: errorData,
        duration,
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('External system creation request completed successfully', {
      success: true,
      duration,
      systemId: data.id,
      systemType: data.system_type,
    });

    return NextResponse.json(data);
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.error('Error in external system creation API route', {
      error: String(error),
      duration,
    });
    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}
