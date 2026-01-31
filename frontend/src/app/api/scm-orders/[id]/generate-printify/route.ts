import { NextRequest, NextResponse } from 'next/server';
import { keyLoader } from '@/lib/key-loader';
import { generateBackendSignature } from '@/lib/signature';
import { jwtUtilsServer } from '@/lib/jwt-utils-server';
import { frontendLogger } from '@/lib/frontend-logger';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: scmOrderHashid } = await params;
    const requestBody = await request.json();
    frontendLogger.info('🔄 尝试生成 Printify 订单', {
      scmOrderHashid,
      selectedItems: requestBody.selected_items?.length,
    });

    // 获取前端 JWT token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      frontendLogger.error('❌ 缺少或无效的授权头');
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    const frontendToken = authHeader.substring(7);

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

    // 生成后端签名
    const timestamp = Math.floor(Date.now() / 1000);
    const nonce = Math.random().toString(36).substring(2, 15);
    const backendPath = `/api/v1/scm-orders/${scmOrderHashid}/generate-printify`;
    const signatureString = `POST${backendPath}${timestamp}${nonce}${tenantName}${JSON.stringify(requestBody)}`;

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
    frontendLogger.info('➡️ 转发生成 Printify 订单请求到后端', {
      backendUrl,
      scmOrderHashid,
      selectedItemsCount: requestBody.selected_items?.length,
    });

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
      body: JSON.stringify(requestBody),
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      frontendLogger.error('❌ 后端 API 错误', {
        status: backendResponse.status,
        errorText,
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
    frontendLogger.info('✅ Printify 订单生成成功', {
      scmOrderHashid,
      printifyOrderId: data.printify_order_id,
      selectedItemsCount: data.selected_items_count,
    });
    return NextResponse.json(data);
  } catch (error: any) {
    frontendLogger.error('❌ 生成 Printify 订单 API 错误', {
      error: error.message,
    });
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
