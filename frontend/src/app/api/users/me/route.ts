import { NextRequest, NextResponse } from 'next/server';
import crypto from 'crypto';
import Hashids from 'hashids';
import { jwtDecode } from 'jwt-decode';
import { createLogger } from '@/lib/logger';
import { keyLoader } from '@/lib/key-loader';

const logger = createLogger('users.me');

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

// JWT 载荷类型
interface JWTPayload {
  sub: string;
  tenant_id: number;
  exp: number;
  type: 'access' | 'refresh';
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();
  logger.requestStart(request.method, request.url);
  
  try {
    // 获取 Authorization 头
    const authHeader = request.headers.get('Authorization');
    if (!authHeader) {
      logger.warn('Missing Authorization header');
      return NextResponse.json(
        { error: 'Authorization header is required' },
        { status: 401 }
      );
    }

    // 提取 JWT token
    const token = authHeader.replace('Bearer ', '');
    
    try {
      // 从 JWT 解码获取 tenant_id
      const decoded = jwtDecode<JWTPayload>(token);
      const tenantId = decoded.tenant_id;
      
      logger.info('JWT decoded successfully', { 
        userId: decoded.sub,
        tenantId: tenantId,
        tokenType: decoded.type
      });

      // 根据 tenant_id 找到对应的租户配置
      const tenantName = Object.keys(TENANT_CONFIG).find(
        name => TENANT_CONFIG[name as keyof typeof TENANT_CONFIG].id === tenantId
      );

      if (!tenantName) {
        logger.error('Tenant not found', { tenantId });
        return NextResponse.json(
          { error: 'Tenant not found' },
          { status: 404 }
        );
      }

      const tenantConfig = TENANT_CONFIG[tenantName as keyof typeof TENANT_CONFIG];
      
      logger.info('Tenant found', { tenantName, tenantId });

      // 使用 RSA 签名认证（正确的架构）
      logger.info('Using RSA signature authentication for /me endpoint');
      
      // 生成签名参数
      const nonce = generateNonce();
      const timestamp = Math.floor(Date.now() / 1000);
      const method = 'GET';
      const path = '/api/v1/auth/me';
      const body = ''; // GET 请求没有 body

      // 构造签名字符串（与 login 路由保持一致）
      const signatureString = `${method.toUpperCase()}${path}${timestamp}${nonce}${tenantId}${body}`;
      
      logger.debug('Signature string constructed', {
        signatureStringLength: signatureString.length,
        method: method.toUpperCase(),
        path,
        timestamp,
        nonce,
        tenantId,
        bodyLength: body.length,
        body: body,
        signatureString: signatureString
      });

      // 从文件加载私钥并生成 RSA 签名
      const privateKey = keyLoader.loadTenantPrivateKey(tenantName);
      const signature = generateSignature(privateKey, signatureString);
      
      logger.info('Signature generated successfully', {
        signatureLength: signature.length,
        tenantName,
        tenantId
      });

      // 编码 tenant ID
      const encodedTenantId = hashids.encode(tenantId);
      
      logger.debug('Tenant ID encoded', {
        originalId: tenantId,
        encodedId: encodedTenantId
      });

      // 转发到后端 API（使用 RSA 签名认证）
      const backendResponse = await fetch('http://localhost:8000/api/v1/auth/me', {
        method: 'GET',
        headers: {
          'X-Tenant-ID': encodedTenantId,
          'X-Timestamp': timestamp.toString(),
          'X-Nonce': nonce,
          'X-Signature': signature,
          'Content-Type': 'application/json',
        },
      });

      const responseData = await backendResponse.json();

      if (backendResponse.ok) {
        logger.info('User profile retrieved successfully');
        const duration = Date.now() - startTime;
        logger.requestComplete(request.method, request.url, backendResponse.status, duration);
        return NextResponse.json(responseData);
      } else {
        logger.warn('User profile request failed', { 
          status: backendResponse.status,
          error: responseData.detail || responseData.error 
        });
        const duration = Date.now() - startTime;
        logger.requestError(request.method, request.url, new Error(responseData.detail || 'User profile request failed'), duration);
        return NextResponse.json(
          { error: responseData.detail || 'User profile request failed' },
          { status: backendResponse.status }
        );
      }
    } catch (jwtError) {
      logger.error('JWT decode failed', { error: String(jwtError) });
      return NextResponse.json(
        { error: 'Invalid JWT token' },
        { status: 401 }
      );
    }
  } catch (error) {
    logger.error('User profile request error', { error: error instanceof Error ? error.message : 'Unknown error' });
    const duration = Date.now() - startTime;
    logger.requestError(request.method, request.url, error instanceof Error ? error : new Error('Unknown error'), duration);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
