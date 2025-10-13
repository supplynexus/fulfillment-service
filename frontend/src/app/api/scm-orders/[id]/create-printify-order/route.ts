import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';

const logger = createLogger('api.scm-orders.create-printify-order');

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const startTime = Date.now();
  
  try {
    logger.requestStart('POST', request.url, {
      scm_order_id: params.id
    });

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
    
    logger.info('🔍 开始处理创建 Printify 发货单请求', { 
      tenantName, 
      userId, 
      scm_order_id: params.id 
    });

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const bodyString = '';
    const signatureString = `POST/api/v1/scm-orders/${params.id}/create-printify-order${timestamp}${nonce}${tenantName}${bodyString}`;
    
    const privateKey = await keyLoader.getTenantPrivateKey(tenantName);
    const signature = generateBackendSignature(privateKey, signatureString, timestamp, nonce, tenantName);

    // 调用后端 API
    const backendUrl = `${process.env.BACKEND_API_URL || 'http://backend:8000'}/api/v1/scm-orders/${params.id}/create-printify-order`;
    
    logger.info('📡 调用后端创建 Printify 发货单 API', { 
      backendUrl,
      scm_order_id: params.id
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
      logger.requestComplete('POST', request.url, backendResponse.status, duration);
      logger.info('✅ Printify 发货单创建成功', { 
        success: responseData.success,
        printify_order_id: responseData.printify_order_id,
        external_order_id: responseData.external_order_id
      });
      
      return NextResponse.json(responseData);
    } else {
      logger.error('❌ 后端创建 Printify 发货单失败', { 
        status: backendResponse.status,
        error: responseData 
      });
      
      return NextResponse.json(
        { 
          success: false, 
          message: responseData.detail || '创建 Printify 发货单失败',
          error: responseData 
        },
        { status: backendResponse.status }
      );
    }

  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('❌ 创建 Printify 发货单请求处理失败', { 
      error: error.message,
      duration,
      scm_order_id: params.id
    });
    
    return NextResponse.json(
      { 
        success: false, 
        message: 'Internal server error',
        error: error.message 
      },
      { status: 500 }
    );
  }
}
