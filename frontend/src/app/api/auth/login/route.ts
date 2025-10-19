import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('auth.login');

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
      contentType: request.headers.get('content-type'),
    });

    // 解析表单数据
    let formData: FormData;
    try {
      // 添加更详细的调试信息
      const contentType = request.headers.get('content-type');
      const contentLength = request.headers.get('content-length');

      logger.info('Attempting to parse FormData', {
        contentType,
        contentLength,
        hasBody: !!request.body,
      });

      formData = await request.formData();

      logger.info('FormData parsed successfully', {
        formDataKeys: Array.from(formData.keys()),
        formDataSize: Array.from(formData.entries()).length,
      });
    } catch (formDataError) {
      logger.error('FormData parsing failed', {
        error: String(formDataError),
        contentType: request.headers.get('content-type'),
        contentLength: request.headers.get('content-length'),
        errorType:
          formDataError instanceof Error
            ? formDataError.constructor.name
            : 'Unknown',
        errorStack:
          formDataError instanceof Error ? formDataError.stack : undefined,
      });
      return NextResponse.json(
        { detail: 'Invalid form data format' },
        { status: 400 }
      );
    }

    const username = formData.get('username') as string;
    const password = formData.get('password') as string;
    const tenantName = formData.get('tenant_name') as string;

    logger.info('Form data received', {
      username,
      tenantName,
      hasPassword: !!password,
      formDataKeys: Array.from(formData.keys()),
    });

    if (!username || !password || !tenantName) {
      logger.warn('Missing required fields', {
        username: !!username,
        password: !!password,
        tenantName: !!tenantName,
      });
      return NextResponse.json(
        { detail: '用户名、密码和租户名称都是必需的' },
        { status: 400 }
      );
    }

    // 生成签名
    logger.info('Generating backend signature for tenant', { tenantName });

    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 12);
    const body = `username=${username}&password=${password}&tenant_name=${tenantName}`;

    // 使用后端期望的路径格式
    const backendPath = '/api/v1/auth/login';
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${body}`;

    logger.info('🔍 Frontend 签名生成调试信息:', {
      timestamp,
      nonce,
      body,
      backendPath,
      signatureString,
      signatureStringLength: signatureString.length,
      tenantName,
    });

    let privateKey;
    try {
      privateKey = await keyLoader.getTenantPrivateKey(tenantName);
      logger.info('Private key loaded successfully', { tenantName });
    } catch (keyError) {
      logger.error('Failed to load private key', {
        tenantName,
        error: String(keyError),
        errorStack: keyError instanceof Error ? keyError.stack : undefined,
      });
      return NextResponse.json(
        { detail: `Failed to load private key: ${keyError}` },
        { status: 500 }
      );
    }

    let signature;
    try {
      signature = generateBackendSignature(
        privateKey,
        signatureString,
        timestamp,
        nonce,
        tenantName
      );
      logger.info('Backend signature generated successfully', { tenantName });
    } catch (signatureError) {
      logger.error('Failed to generate signature', {
        tenantName,
        error: String(signatureError),
        errorStack: signatureError instanceof Error ? signatureError.stack : undefined,
      });
      return NextResponse.json(
        { detail: `Failed to generate signature: ${signatureError}` },
        { status: 500 }
      );
    }

    logger.info('Backend signature generated successfully', {
      signatureLength: signature.length,
      signature: signature.substring(0, 50) + '...', // 只显示前50个字符
      tenantName,
    });

    // 转发到后端
    const backendUrl =
      process.env.BACKEND_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://backend:8000';
    const backendEndpoint = `${backendUrl}${backendPath}`;
    logger.info('Forwarding request to backend', { backendEndpoint });

    const response = await fetch(backendEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Signature': signature,
        'X-Tenant-Name': tenantName,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
      },
      body: new URLSearchParams({
        username,
        password,
        tenant_name: tenantName,
      }),
    });

    const duration = Date.now() - startTime;
    logger.info('Backend response received', {
      status: response.status,
      statusText: response.statusText,
      duration: `${duration}ms`,
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ detail: '登录失败' }));
      logger.warn('Backend request failed', {
        status: response.status,
        errorData,
        duration: `${duration}ms`,
      });
      return NextResponse.json(errorData, { status: response.status });
    }

    const backendData = await response.json();
    logger.info('Backend authentication successful', {
      userId: backendData.user?.id,
      tenantId: backendData.user?.tenant_id,
      tenantName: backendData.tenant_name,
    });

    // 生成 Frontend JWT (使用前端private key)
    logger.info('Generating Frontend JWT using frontend private key');

    try {
      const frontendJWT = jwtUtilsServer.generateToken(
        {
          sub: backendData.user?.id?.toString() || '0',
          tenant_id: backendData.user?.tenant_id,
          email: backendData.user?.email || username,
          tenant_name: backendData.tenant_name || tenantName,
          type: 'access',
        },
        3600
      ); // 1 hour

      logger.info(
        'Frontend JWT access token generated successfully (using frontend private key)',
        {
          tokenLength: frontendJWT.length,
          userId: backendData.user?.id,
          tenantId: backendData.user?.tenant_id,
          jwtSource: 'frontend-generated',
          keyUsed: 'frontend_jwt_private_key.pem',
        }
      );

      const refreshToken = jwtUtilsServer.generateToken(
        {
          sub: backendData.user?.id?.toString() || '0',
          tenant_id: backendData.user?.tenant_id,
          email: backendData.user?.email || username,
          tenant_name: backendData.tenant_name || tenantName,
          type: 'refresh',
        },
        604800
      ); // 7 days

      logger.info(
        'Frontend JWT refresh token generated successfully (using frontend private key)',
        {
          tokenLength: refreshToken.length,
          userId: backendData.user?.id,
          tenantId: backendData.user?.tenant_id,
          jwtSource: 'frontend-generated',
          keyUsed: 'frontend_jwt_private_key.pem',
        }
      );

      // 返回 Frontend JWT
      const frontendResponse = {
        access_token: frontendJWT,
        refresh_token: refreshToken,
        token_type: 'bearer',
        user: backendData.user,
        tenant_name: backendData.tenant_name || tenantName,
      };

      logger.info('Frontend response prepared', {
        hasAccessToken: !!frontendJWT,
        hasRefreshToken: !!refreshToken,
        hasUser: !!backendData.user,
        responseKeys: Object.keys(frontendResponse),
      });

      logger.requestComplete(
        'POST',
        '/api/auth/login',
        response.status,
        duration / 1000,
        {
          tenantName,
          username,
          hasAccessToken: !!frontendJWT,
          jwtGenerated: true,
        }
      );

      return NextResponse.json(frontendResponse);
    } catch (jwtError) {
      logger.error('JWT generation failed', {
        error: String(jwtError),
        errorStack: jwtError instanceof Error ? jwtError.stack : undefined,
        backendData: {
          userId: backendData.user?.id,
          tenantId: backendData.user?.tenant_id,
          email: backendData.user?.email,
          tenantName: backendData.tenant_name,
        },
      });

      return NextResponse.json({ detail: 'JWT生成失败' }, { status: 500 });
    }
  } catch (error) {
    const duration = Date.now() - startTime;
    logger.requestError('POST', '/api/auth/login', error, duration / 1000, {
      errorMessage: error instanceof Error ? error.message : String(error),
      errorStack: error instanceof Error ? error.stack : undefined,
    });

    return NextResponse.json({ detail: '服务器内部错误' }, { status: 500 });
  }
}
