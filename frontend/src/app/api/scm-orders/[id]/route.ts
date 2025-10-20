import { NextRequest, NextResponse } from 'next/server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { frontendLogger } from '@/lib/frontend-logger';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: scmOrderHashid } = await params;
    frontendLogger.info('🔄 尝试获取 SCM 订单详情', { scmOrderHashid });

    // 获取前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      frontendLogger.error('❌ 缺少或无效的授权头');
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
      frontendLogger.info('✅ JWT 验证成功', {
        userId: decodedToken.sub,
        tenantName: decodedToken.tenant_name,
      });
    } catch (error: any) {
      frontendLogger.error('❌ JWT 验证失败', { error: error.message });
      return NextResponse.json({ error: 'Invalid JWT token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/scm-orders/${scmOrderHashid}`;
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
    frontendLogger.info('➡️ 转发获取请求到后端', {
      backendUrl,
      scmOrderHashid,
    });

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
      frontendLogger.error('❌ 后端 API 错误', {
        status: backendResponse.status,
        errorText,
      });
      return NextResponse.json(
        {
          error: `Backend API error: ${backendResponse.status}`,
          detail: errorText,
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    frontendLogger.info('✅ SCM 订单详情获取成功', { scmOrderHashid });
    return NextResponse.json(data);
  } catch (error: any) {
    frontendLogger.error('❌ 获取 SCM 订单详情 API 错误', {
      error: error.message,
    });
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: scmOrderHashid } = await params;
    frontendLogger.info('🔄 尝试更新 SCM 订单', { scmOrderHashid });

    // 获取前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      frontendLogger.error('❌ 缺少或无效的授权头');
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
      frontendLogger.info('✅ JWT 验证成功', {
        userId: decodedToken.sub,
        tenantName: decodedToken.tenant_name,
      });
    } catch (error: any) {
      frontendLogger.error('❌ JWT 验证失败', { error: error.message });
      return NextResponse.json({ error: 'Invalid JWT token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;

    // 获取请求体
    const requestBody = await request.json();
    frontendLogger.info('📝 更新数据', { requestBody });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/scm-orders/${scmOrderHashid}`;
    const bodyString = JSON.stringify(requestBody);
    const signatureString = `PUT${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

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
    frontendLogger.info('➡️ 转发更新请求到后端', {
      backendUrl,
      scmOrderHashid,
    });

    // 调用后端 API
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

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      frontendLogger.error('❌ 后端 API 错误', {
        status: backendResponse.status,
        errorText,
      });
      return NextResponse.json(
        {
          error: `Backend API error: ${backendResponse.status}`,
          detail: errorText,
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    frontendLogger.info('✅ SCM 订单更新成功', { scmOrderHashid });
    return NextResponse.json(data);
  } catch (error: any) {
    frontendLogger.error('❌ 更新 SCM 订单 API 错误', { error: error.message });
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
    const { id: scmOrderHashid } = await params;
    frontendLogger.info('🔄 尝试删除 SCM 订单', { scmOrderHashid });

    // 获取前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      frontendLogger.error('❌ 缺少或无效的授权头');
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
      frontendLogger.info('✅ JWT 验证成功', {
        userId: decodedToken.sub,
        tenantName: decodedToken.tenant_name,
      });
    } catch (error: any) {
      frontendLogger.error('❌ JWT 验证失败', { error: error.message });
      return NextResponse.json({ error: 'Invalid JWT token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/scm-orders/${scmOrderHashid}`;
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
    frontendLogger.info('➡️ 转发删除请求到后端', {
      backendUrl,
      scmOrderHashid,
    });

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
      frontendLogger.error('❌ 后端 API 错误', {
        status: backendResponse.status,
        errorText,
      });
      return NextResponse.json(
        {
          error: `Backend API error: ${backendResponse.status}`,
          detail: errorText,
        },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    frontendLogger.info('✅ SCM 订单删除成功', {
      scmOrderHashid,
      response: data,
    });
    return NextResponse.json(data);
  } catch (error: any) {
    frontendLogger.error('❌ 删除 SCM 订单 API 错误', { error: error.message });
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
