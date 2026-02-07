import { NextRequest, NextResponse } from 'next/server';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { frontendLogger } from '@/lib/frontend-logger';

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> | { id: string } }
) {
  const startTime = Date.now();
  const params = await Promise.resolve(context.params);
  const scmOrderId = params.id;
  
  try {
    frontendLogger.info('🚀 开始处理 SCM 订单解绑 Printify 订单请求', { scmOrderId });

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

    // 生成后端签名（POST 无 body 时 bodyString 为空字符串，但必须参与签名字符串以与后端校验一致）
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const signatureString = `POST/api/v1/scm-orders/${scmOrderId}/unbind-printify-order${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);

    frontendLogger.info('✅ 后端签名生成成功', { timestamp, nonce });

    // 构建后端URL
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/scm-orders/${scmOrderId}/unbind-printify-order`;

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

    frontendLogger.info('✅ SCM 订单解绑 Printify 订单成功', {
      scmOrderId,
      status: backendResponse.status,
      duration,
    });

    return NextResponse.json(responseData);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    frontendLogger.error('❌ SCM 订单解绑 Printify 订单失败', {
      scmOrderId,
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
