import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';

const logger = createLogger('api.printify-sync-status');

export async function GET(request: NextRequest) {
  const startTime = Date.now();
  logger.requestStart(request.method, request.url);
  
  try {
    // 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const frontendToken = authHeader.substring(7);
    logger.info('Verifying JWT token', { tokenLength: frontendToken.length });
    
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
      logger.info('JWT token verified successfully');
    } catch (jwtError) {
      logger.error('JWT verification failed', { error: String(jwtError) });
      return NextResponse.json({ error: 'Invalid token', details: String(jwtError) }, { status: 401 });
    }
    
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('处理 Printify 同步状态请求', { tenantName, userId });

    // 获取查询参数
    const { searchParams } = new URL(request.url);
    const external_system_id_hashid = searchParams.get('external_system_id_hashid');

    if (!external_system_id_hashid) {
      return NextResponse.json(
        { error: 'external_system_id_hashid is required' },
        { status: 400 }
      );
    }

    // 构建后端 API 路径
    const backendPath = `/api/v1/printify-sync/sync-status`;
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8000'}${backendPath}`;
    
    logger.info('Backend URL configuration', { 
      backendUrl, 
      backendPath,
      envBackendUrl: process.env.BACKEND_URL 
    });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const queryString = `external_system_id_hashid=${external_system_id_hashid}`;
    const signatureString = `GET${backendPath}${timestamp}${nonce}${tenantName}`;

    logger.info('Generating backend signature', { 
      tenantName, 
      timestamp, 
      nonce, 
      signatureString 
    });

    let privateKey;
    try {
      privateKey = await keyLoader.getTenantPrivateKey(tenantName);
      logger.info('Private key loaded successfully');
    } catch (keyError) {
      logger.error('Failed to load private key', { error: String(keyError) });
      return NextResponse.json({ error: 'Failed to load private key', details: String(keyError) }, { status: 500 });
    }

    let signature;
    try {
      signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);
      logger.info('Backend signature generated successfully');
    } catch (signatureError) {
      logger.error('Failed to generate backend signature', { error: String(signatureError) });
      return NextResponse.json({ error: 'Failed to generate signature', details: String(signatureError) }, { status: 500 });
    }

    // 调用后端 API
    logger.info('Calling backend API', { 
      url: `${backendUrl}?${queryString}`,
      headers: {
        'X-Tenant-Name': tenantName,
        'X-User-ID': userId,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature.substring(0, 20) + '...' // 只显示签名的前20个字符
      }
    });

    let backendResponse;
    try {
      backendResponse = await fetch(`${backendUrl}?${queryString}`, {
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
      logger.info('Backend API response received', { 
        status: backendResponse.status,
        statusText: backendResponse.statusText 
      });
    } catch (fetchError) {
      logger.error('Failed to call backend API', { error: String(fetchError) });
      return NextResponse.json(
        { error: 'Failed to call backend API', details: String(fetchError) },
        { status: 500 }
      );
    }

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('后端 API 调用失败', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });
      return NextResponse.json(
        { error: 'Backend API call failed', details: errorText },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    const duration = (Date.now() - startTime) / 1000;
    logger.requestComplete(request.method, request.url, backendResponse.status, duration);

    return NextResponse.json(data);
  } catch (error) {
    logger.error('处理 Printify 同步状态请求失败', { error: String(error) });
    return NextResponse.json(
      { error: 'Internal server error', details: String(error) },
      { status: 500 }
    );
  }
}
