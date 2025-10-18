import { NextRequest, NextResponse } from 'next/server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: orderHashid } = await params;

    // 获取前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);

    // 验证前端 JWT token
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      console.error('JWT verification failed:', error);
      return NextResponse.json({ error: 'Invalid JWT token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/orders/${orderHashid}`;
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 构建后端 URL
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8000'}${backendPath}`;

    // 调用后端 API
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
      console.error('Backend API error:', backendResponse.status, errorText);
      return NextResponse.json(
        {
          error: `Backend API error: ${backendResponse.status}`,
          detail: errorText,
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Order get API error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: orderHashid } = await params;

    // 获取前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);

    // 验证前端 JWT token
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      console.error('JWT verification failed:', error);
      return NextResponse.json({ error: 'Invalid JWT token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/orders/${orderHashid}`;
    const signatureString = `DELETE${backendPath}${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 构建后端 URL
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8000'}${backendPath}`;

    // 调用后端 API
    const backendResponse = await fetch(backendUrl, {
      method: 'DELETE',
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
      console.error('Backend API error:', backendResponse.status, errorText);
      return NextResponse.json(
        {
          error: `Backend API error: ${backendResponse.status}`,
          detail: errorText,
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Order delete API error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
