import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.printify-orders.sync-logistics');

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.requestStart('POST', request.url);

    // 获取前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('❌ 缺少认证头');
      return NextResponse.json(
        { success: false, message: 'Missing authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);

    // 验证前端 JWT token
    const decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    const { tenant_name: tenantName, sub: userId } = decodedToken;

    logger.info('🔍 开始处理同步 Printify 订单物流信息请求', {
      tenantName,
      userId,
    });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const signatureString = `POST/api/v1/printify/orders/sync-logistics${timestamp}${nonce}${tenantName}${bodyString}`;

    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    // 调用后端 API
    const backendUrl = `${process.env.BACKEND_API_URL || 'http://backend:8000'}/api/v1/printify/orders/sync-logistics`;

    logger.info('📡 调用后端同步 Printify 订单物流信息 API', {
      backendUrl,
    });

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

    if (backendResponse.ok) {
      logger.requestComplete(
        'POST',
        request.url,
        backendResponse.status,
        duration
      );
      logger.info('✅ Printify 订单物流信息同步成功', {
        success: responseData.success,
        syncedCount: responseData.synced_count,
        totalOrders: responseData.total_orders,
        errorCount: responseData.error_count,
      });

      return NextResponse.json(responseData);
    } else {
      logger.error('❌ 后端同步 Printify 订单物流信息失败', {
        status: backendResponse.status,
        error: responseData,
      });

      return NextResponse.json(
        {
          success: false,
          message: responseData.detail || '同步 Printify 订单物流信息失败',
          error: responseData,
        },
        { status: backendResponse.status }
      );
    }
  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('❌ 同步 Printify 订单物流信息请求处理失败', {
      error: error.message,
      duration,
    });

    return NextResponse.json(
      {
        success: false,
        message: 'Internal server error',
        error: error.message,
      },
      { status: 500 }
    );
  }
}
