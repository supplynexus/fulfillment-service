import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { frontendLogger } from '@/lib/frontend-logger';

const logger = createLogger('api.automation.steps');

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    frontendLogger.info('🚀 开始获取自动化步骤列表');

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

    // 获取查询参数
    const { searchParams } = new URL(request.url);
    const category = searchParams.get('category');

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = category
      ? `/api/v1/automation/steps?category=${category}`
      : '/api/v1/automation/steps';
    const bodyString = '';
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

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
    frontendLogger.info('✅ 获取自动化步骤列表成功', {
      count: data.length,
      duration,
    });

    logger.requestComplete('GET', '/api/automation/steps', backendResponse.status, duration);

    return NextResponse.json(data);
  } catch (error: any) {
    const duration = Date.now() - startTime;
    frontendLogger.error('❌ 获取自动化步骤列表失败', {
      error: error.message,
      duration,
    });

    return NextResponse.json(
      { error: 'Internal server error', detail: error.message },
      { status: 500 }
    );
  }
}




