import { NextRequest, NextResponse } from 'next/server';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { frontendLogger } from '@/lib/frontend-logger';

/**
 * POST: 从 Printify 同步订单创建 SCM 订单并绑定（无请求体）
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const startTime = Date.now();
  const { id: printifyOrderId } = await params;

  try {
    frontendLogger.info('🚀 开始处理「从 Printify 订单创建 SCM 并绑定」请求', {
      printifyOrderId,
    });

    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      frontendLogger.error('❌ 缺少认证头');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const token = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(token);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const signatureString = `POST/api/v1/printify/${printifyOrderId}/create-scm-and-bind${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/printify/${printifyOrderId}/create-scm-and-bind`;

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
      body: bodyString || undefined,
    });

    const responseData = await backendResponse.json();
    const duration = Date.now() - startTime;

    if (!backendResponse.ok) {
      frontendLogger.error('❌ 后端 create-scm-and-bind 失败', {
        status: backendResponse.status,
        responseData,
        duration,
      });
      return NextResponse.json(
        { error: responseData.detail || 'Backend API error' },
        { status: backendResponse.status }
      );
    }

    frontendLogger.info('✅ 从 Printify 订单创建 SCM 并绑定成功', {
      printifyOrderId,
      duration,
    });
    return NextResponse.json(responseData);
  } catch (error: any) {
    const duration = Date.now() - startTime;
    frontendLogger.error('❌ create-scm-and-bind 失败', {
      printifyOrderId,
      error: error.message,
      duration,
    });
    if (
      error.message?.includes('JWT') ||
      error.message?.includes('token') ||
      error.message?.includes('signature')
    ) {
      return NextResponse.json(
        { error: error.message || 'Authentication error' },
        { status: 401 }
      );
    }
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
