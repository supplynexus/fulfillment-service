import { NextRequest, NextResponse } from 'next/server';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { frontendLogger } from '@/lib/frontend-logger';

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const startTime = Date.now();
  const printifyOrderId = params.id;
  
  try {
    frontendLogger.info('🚀 开始处理 Printify 订单解绑 SCM 订单请求', { printifyOrderId });

    // 验证JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      frontendLogger.error('❌ 缺少认证头');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const token = authHeader.substring(7);
    const decodedToken = jwtUtilsServer.verifyToken(token);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    frontendLogger.info('✅ JWT验证成功', { tenantName, userId });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const signatureString = `POST/api/v1/printify/${printifyOrderId}/unbind-scm-order${timestamp}${nonce}${tenantName}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);

    frontendLogger.info('✅ 后端签名生成成功', { timestamp, nonce });

    // 构建后端URL（后端路由前缀为 /printify）
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/printify/${printifyOrderId}/unbind-scm-order`;

    // 调用后端API
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
    });

    const responseData = await backendResponse.json();
    const duration = Date.now() - startTime;

    if (!backendResponse.ok) {
      frontendLogger.error('❌ 后端API调用失败', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        responseData,
        duration,
      });
      return NextResponse.json(
        { error: responseData.detail || 'Backend API error' },
        { status: backendResponse.status }
      );
    }

    frontendLogger.info('✅ Printify 订单解绑 SCM 订单成功', {
      printifyOrderId,
      status: backendResponse.status,
      duration,
    });

    return NextResponse.json(responseData);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    frontendLogger.error('❌ Printify 订单解绑 SCM 订单失败', {
      printifyOrderId,
      error: error.message,
      duration,
    });

    // JWT 相关错误返回 401
    if (error.message.includes('JWT') || error.message.includes('token') || error.message.includes('signature')) {
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
