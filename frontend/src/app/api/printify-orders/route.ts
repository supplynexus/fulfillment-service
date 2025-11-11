import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.printify-orders');

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
      contentType: request.headers.get('content-type'),
    });

    // 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      logger.error('Invalid frontend token', { error: String(error) });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Frontend JWT verified successfully', {
      userId,
      tenantName,
      tokenType: 'access',
    });

    // 获取查询参数
    const { searchParams } = new URL(request.url);
    const page = searchParams.get('page') || '1';
    const limit = searchParams.get('limit') || '20';
    const status = searchParams.get('status');
    const search = searchParams.get('search');

    // 构建后端请求参数
    const backendParams = new URLSearchParams({
      page,
      limit,
    });

    if (status) {
      backendParams.append('status', status);
    }
    if (search) {
      backendParams.append('search', search);
    }

    // 对于 GET 请求，签名字符串中的 body 应该是空字符串
    const bodyString = '';
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);

    // 构建签名字符串
    const signatureString = `GET/api/v1/printify/orders${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'GET',
      path: '/api/v1/printify/orders',
      timestamp,
      nonce,
      tenantName,
      bodyString,
      bodyStringLength: bodyString.length,
      signatureString,
      signatureStringLength: signatureString.length,
    });

    // 获取租户私钥
    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);

    // 生成后端签名
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    logger.info('🔍 前端签名生成完成', {
      signatureLength: signature.length,
      signature: signature.substring(0, 50) + '...',
      tenantName,
    });

    // 构建后端请求 URL
    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/printify/orders?${backendParams.toString()}`;

    logger.info('📡 调用后端 Printify 订单 API', {
      backendEndpoint: backendUrl,
    });

    // 发送请求到后端
    const backendResponse = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
        'X-User-ID': userId.toString(),
      },
    });

    const responseTime = Date.now() - startTime;
    logger.info('Backend response received', {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      duration: `${responseTime}ms`,
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('Backend request failed', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('Request completed', {
      method: request.method,
      url: request.url,
      statusCode: 200,
      duration: `${responseTime}ms`,
      tenantName,
      hasData: !!data,
      ordersCount: data.orders?.length || 0,
    });

    return NextResponse.json(data);
  } catch (error) {
    const responseTime = Date.now() - startTime;
    logger.error('Request failed', {
      error: String(error),
      errorMessage: error instanceof Error ? error.message : 'Unknown error',
      duration: `${responseTime}ms`,
    });

    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    // 添加调试日志
    console.log('🔍 Next.js API路由被调用', {
      method: request.method,
      url: request.url,
    });

    logger.requestStart(request.method, request.url, {
      userAgent: request.headers.get('user-agent'),
      contentType: request.headers.get('content-type'),
    });

    // 验证前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      logger.error('Missing or invalid authorization header');
      return NextResponse.json(
        { detail: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);
    let decodedToken;
    try {
      decodedToken = jwtUtilsServer.verifyToken(frontendToken);
    } catch (error) {
      logger.error('Invalid frontend token', { error: String(error) });
      return NextResponse.json({ detail: 'Invalid token' }, { status: 401 });
    }

    const { tenant_name: tenantName, sub: userId } = decodedToken;
    logger.info('Frontend JWT verified successfully', {
      userId,
      tenantName,
      tokenType: 'access',
    });

    // 获取请求体
    const requestBody = await request.json();
    
    // 调试日志：打印请求体内容
    logger.info('🔍 请求体调试信息', {
      requestBodyKeys: Object.keys(requestBody),
      hasPrintifyData: !!requestBody.printify_data,
      hasCustomerEmail: !!requestBody.customer_email,
      hasTotalPrice: !!requestBody.total_price,
      hasShippingAddress: !!requestBody.shipping_address,
      hasBillingAddress: !!requestBody.billing_address,
      hasTrackingNumber: !!requestBody.tracking_number,
      hasTrackingUrl: !!requestBody.tracking_url,
      hasCarrier: !!requestBody.carrier,
      hasShippedAt: !!requestBody.shipped_at,
      hasDeliveredAt: !!requestBody.delivered_at,
      trackingNumberValue: requestBody.tracking_number,
      trackingUrlValue: requestBody.tracking_url,
      carrierValue: requestBody.carrier,
      externalOrderId: requestBody.external_order_id,
      externalSystemId: requestBody.external_system_id,
    });
    
    // 根据请求内容判断请求类型
    // 批量删除请求：有 order_ids 数组，且 action 为 'delete'
    const isBatchDelete = requestBody.order_ids && Array.isArray(requestBody.order_ids) && 
                          requestBody.action === 'delete';
    
    // 更新 SCM 状态请求：有 order_ids 数组，但没有 action 字段或 action 不是 'delete'
    const isUpdateScmStatus = requestBody.order_ids && Array.isArray(requestBody.order_ids) && !isBatchDelete;
    
    // 更新物流信息请求：有external_order_id和external_system_id，并且有物流相关字段
    // 修改判断条件：只有包含物流相关字段（不包括status）才认为是更新物流信息请求
    const hasTrackingFields = 'tracking_number' in requestBody || 'tracking_url' in requestBody || 
                             'carrier' in requestBody || 'shipped_at' in requestBody || 
                             'delivered_at' in requestBody;
    
    const isUpdateTracking = requestBody.external_order_id && requestBody.external_system_id && hasTrackingFields;
    
    // 调试日志：打印路由判断结果
    logger.info('🔍 路由判断调试信息', {
      isBatchDelete,
      isUpdateScmStatus,
      isUpdateTracking,
      hasExternalOrderId: !!requestBody.external_order_id,
      hasExternalSystemId: !!requestBody.external_system_id,
      hasTrackingFields,
      action: requestBody.action,
      trackingNumberIn: 'tracking_number' in requestBody,
      trackingUrlIn: 'tracking_url' in requestBody,
      carrierIn: 'carrier' in requestBody,
      shippedAtIn: 'shipped_at' in requestBody,
      deliveredAtIn: 'delivered_at' in requestBody,
      statusIn: 'status' in requestBody,
    });
    
    if (isBatchDelete) {
      logger.info('🔍 开始批量删除 Printify 订单', {
        orderIds: requestBody.order_ids,
        tenantName,
        userId,
      });
    } else if (isUpdateScmStatus) {
      logger.info('🔍 开始更新SCM订单状态', {
        orderIds: requestBody.order_ids,
        tenantName,
        userId,
      });
    } else if (isUpdateTracking) {
      logger.info('🔍 开始更新Printify订单物流信息', {
        externalOrderId: requestBody.external_order_id,
        tenantName,
        userId,
      });
    } else {
      logger.info('🔍 开始保存 Printify 订单到数据库', {
        externalOrderId: requestBody.external_order_id,
        tenantName,
        userId,
      });
    }

    // 构建签名字符串
    const bodyString = JSON.stringify(requestBody);
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    
    // 根据请求类型选择不同的后端路径
    let backendPath;
    if (isBatchDelete) {
      backendPath = '/api/v1/printify/orders/batch-delete';
    } else if (isUpdateScmStatus) {
      backendPath = '/api/v1/printify/update-scm-status';
    } else if (isUpdateTracking) {
      backendPath = '/api/v1/printify/update-tracking';
    } else {
      backendPath = '/api/v1/printify/save';
    }
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${bodyString}`;

    logger.info('🔍 前端签名生成调试信息', {
      method: 'POST',
      path: backendPath,
      timestamp,
      nonce,
      tenantName,
      bodyStringLength: bodyString.length,
      signatureString,
      signatureStringLength: signatureString.length,
    });

    // 获取租户私钥
    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);

    // 生成后端签名
    const signature = generateBackendSignature(
      privateKey,
      signatureString,
      timestamp,
      nonce,
      tenantName
    );

    logger.info('🔍 前端签名生成完成', {
      signatureLength: signature.length,
      signature: signature.substring(0, 50) + '...',
      tenantName,
    });

    // 构建后端请求 URL
    const backendUrl = `${process.env.BACKEND_API_URL}${backendPath}`;

    logger.info('📡 调用后端 Printify API', {
      backendEndpoint: backendUrl,
      requestType: isBatchDelete ? 'batch-delete' :
                   isUpdateScmStatus ? 'update-scm-status' :
                   isUpdateTracking ? 'update-tracking' : 'save-order',
    });

    // 发送请求到后端
    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Name': tenantName,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'X-Signature': signature,
        'X-User-ID': userId.toString(),
      },
      body: bodyString,
    });

    const responseTime = Date.now() - startTime;
    logger.info('Backend response received', {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      duration: `${responseTime}ms`,
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      logger.error('Backend request failed', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });
      return NextResponse.json(
        { detail: 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const data = await backendResponse.json();
    logger.info('Request completed', {
      method: request.method,
      url: request.url,
      statusCode: 200,
      duration: `${responseTime}ms`,
      tenantName,
      hasData: !!data,
      orderId: data.order_id,
    });

    return NextResponse.json(data);
  } catch (error) {
    const responseTime = Date.now() - startTime;
    logger.error('Request failed', {
      error: String(error),
      errorMessage: error instanceof Error ? error.message : 'Unknown error',
      duration: `${responseTime}ms`,
    });

    return NextResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    );
  }
}