import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { frontendLogger } from '@/lib/frontend-logger';

const logger = createLogger('api.automation.trigger');

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ step_key: string }> }
) {
  const startTime = Date.now();
  const { step_key } = await params;

  try {
    frontendLogger.info('🚀 开始手动触发自动化步骤', { step_key });

    // 获取前端 JWT token
    const frontendToken = request.headers
      .get('authorization')
      ?.replace('Bearer ', '');
    if (!frontendToken) {
      frontendLogger.error('❌ 缺少授权头');
      return NextResponse.json(
        { error: 'Missing authorization header' },
        { status: 401 }
      );
    }

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
    const requestBody = await request.json().catch(() => ({}));
    frontendLogger.info('📦 触发请求数据', { step_key, requestBody });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/automation/configs/${step_key}/trigger`;
    const bodyString = JSON.stringify(requestBody);
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 构建后端 URL
    const backendUrl = `${process.env.BACKEND_API_URL || 'http://localhost:8000'}${backendPath}`;
    frontendLogger.info('➡️ 转发请求到后端', { backendUrl });

    // 调用后端 API
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
      const errorText = await backendResponse.text();
      frontendLogger.error('❌ 后端 API 错误', {
        status: backendResponse.status,
        errorText,
        duration,
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
    frontendLogger.info('✅ 手动触发自动化步骤成功', {
      step_key,
      taskId: data.task_id,
      duration,
    });

    logger.requestComplete(
      'POST',
      `/api/automation/configs/${step_key}/trigger`,
      backendResponse.status,
      duration
    );

    return NextResponse.json(data);
  } catch (error: any) {
    const duration = Date.now() - startTime;
    frontendLogger.error('❌ 手动触发自动化步骤失败', {
      error: error.message,
      step_key,
      duration,
    });

    return NextResponse.json(
      { error: 'Internal server error', detail: error.message },
      { status: 500 }
    );
  }
}















