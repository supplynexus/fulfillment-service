import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';
import Hashids from 'hashids';
import { createLogger, setRequestId, generateRequestId } from '@/lib/logger';
import { keyLoader } from '@/lib/key-loader';

// 创建日志记录器
const logger = createLogger('auth.login');

// 租户配置（只包含 ID，私钥从文件加载）
const TENANT_CONFIG = {
  'impeach': {
    id: 1
  }
};

// 创建 hashids 实例（使用与后端相同的配置）
const hashids = new Hashids('dev-hashids-salt-change-in-prod', 8);

// 生成随机 nonce
function generateNonce(): string {
  return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

// 生成签名
function generateSignature(privateKey: string, signatureString: string): string {
  try {
    const sign = crypto.createSign('RSA-SHA256');
    sign.update(signatureString);
    const rsaSignature = sign.sign(privateKey, 'base64');
    return rsaSignature;
  } catch (error) {
    logger.error('Signature generation failed', { error: String(error) });
    throw new Error('Failed to generate signature');
  }
}

// 生成符合后端期望的签名格式
function generateBackendSignature(privateKey: string, signatureString: string, timestamp: number, nonce: string, tenantId: number): string {
  try {
    // 生成 RSA 签名
    const rsaSignature = generateSignature(privateKey, signatureString);
    
    // 直接返回 RSA 签名，不包装在 JSON 中
    return rsaSignature;
  } catch (error) {
    logger.error('Backend signature generation failed', { error: String(error) });
    throw new Error('Failed to generate backend signature');
  }
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  
  // 确保有请求ID
  if (!request.headers.get('X-Request-ID')) {
    setRequestId(generateRequestId());
  }
  
  logger.requestStart('POST', '/api/auth/login', {
    userAgent: request.headers.get('User-Agent'),
    contentType: request.headers.get('Content-Type'),
  });

  try {
    const formData = await request.formData();
    const username = formData.get('username') as string;
    const password = formData.get('password') as string;
    const tenantName = formData.get('tenant_name') as string;

    logger.info('Form data received', { 
      username, 
      tenantName, 
      hasPassword: !!password,
      formDataKeys: Array.from(formData.keys())
    });

    if (!username || !password || !tenantName) {
      logger.warn('Missing required fields', { 
        hasUsername: !!username, 
        hasPassword: !!password, 
        hasTenantName: !!tenantName 
      });
      return NextResponse.json(
        { detail: '用户名、密码和租户名称都是必需的' },
        { status: 400 }
      );
    }

    // 获取租户配置
    const tenantConfig = TENANT_CONFIG[tenantName as keyof typeof TENANT_CONFIG];
    if (!tenantConfig) {
      logger.warn('Tenant not found', { tenantName });
      return NextResponse.json(
        { detail: '租户不存在' },
        { status: 400 }
      );
    }

    // 生成签名
    logger.info('Generating signature', { tenantName });
    const method = 'POST';
    const path = '/api/v1/auth/login/tenant';
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = generateNonce();
    const tenantId = tenantConfig.id;
    
    // 构造与后端期望格式一致的body字符串
    const body = `username=${username}&password=${password}&tenant_name=${tenantName}`;

    // 格式: METHOD + PATH + TIMESTAMP + NONCE + TENANT_ID + BODY
    const signatureString = `${method.toUpperCase()}${path}${timestamp}${nonce}${tenantId}${body}`;
    
    logger.debug('Signature string constructed', { 
      signatureStringLength: signatureString.length,
      method: method.toUpperCase(),
      path,
      timestamp,
      nonce,
      tenantId,
      bodyLength: body.length,
      body: body
    });
    
    // 从文件加载私钥
    const privateKey = keyLoader.loadTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantId);
    logger.info('Signature generated successfully', { 
      signatureLength: signature.length,
      tenantName,
      tenantId 
    });

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const backendEndpoint = `${backendUrl}/api/v1/auth/login/tenant`;
    logger.info('Forwarding request to backend', { backendEndpoint });

    // 编码租户 ID 为 hashids 格式
    const tenantHashId = hashids.encode(tenantId);
    logger.debug('Tenant ID encoded', { 
      originalId: tenantId, 
      encodedId: tenantHashId 
    });

    const response = await fetch(backendEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Signature': signature,
        'X-Tenant-ID': tenantHashId,
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
      duration: `${duration}ms`
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: '登录失败' }));
      logger.warn('Backend request failed', { 
        status: response.status,
        errorData,
        duration: `${duration}ms`
      });
      return NextResponse.json(errorData, { status: response.status });
    }

    const data = await response.json();
    logger.requestComplete('POST', '/api/auth/login', response.status, duration / 1000, {
      tenantName,
      username,
      hasAccessToken: !!data.access_token
    });
    
    return NextResponse.json(data);

  } catch (error) {
    const duration = Date.now() - startTime;
    logger.requestError('POST', '/api/auth/login', error, duration / 1000, {
      errorMessage: error instanceof Error ? error.message : String(error),
      errorStack: error instanceof Error ? error.stack : undefined
    });
    
    return NextResponse.json(
      { detail: '服务器内部错误' },
      { status: 500 }
    );
  }
}
