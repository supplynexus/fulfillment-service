import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api';

export async function GET(request: NextRequest) {
  try {
    console.log('🔍 前端API路由开始: GET /api/dimension-templates');
    const { searchParams } = new URL(request.url);
    const includeInactive = searchParams.get('include_inactive') === 'true';
    console.log('🔍 前端API参数:', { includeInactive });

    // 从请求头中获取 Authorization token
    const authHeader = request.headers.get('authorization');
    console.log('🔍 获取到的Authorization头:', {
      hasAuth: !!authHeader,
      authLength: authHeader?.length,
      authPrefix: authHeader?.substring(0, 20) + '...',
    });

    if (!authHeader) {
      console.error('❌ 没有找到Authorization头');
      return NextResponse.json({ error: '未授权访问' }, { status: 401 });
    }

    console.log('🔍 调用后端API: /api/v1/product-dimensions/templates');
    const response = await backendApi.get(
      '/api/v1/product-dimensions/templates',
      {
        params: { include_inactive: includeInactive },
        headers: {
          Authorization: authHeader,
        },
      }
    );
    console.log('🔍 后端API响应成功:', response.status);
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('❌ 获取维度模板列表失败:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
      stack: error.stack,
    });
    return NextResponse.json(
      { error: '获取维度模板列表失败', details: error.message },
      { status: error.response?.status || 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    console.log('🔍 前端API路由开始: POST /api/dimension-templates');
    const body = await request.json();
    console.log('🔍 前端API请求体:', body);

    // 从请求头中获取 Authorization token
    const authHeader = request.headers.get('authorization');
    console.log('🔍 获取到的Authorization头:', {
      hasAuth: !!authHeader,
      authLength: authHeader?.length,
      authPrefix: authHeader?.substring(0, 20) + '...',
    });

    if (!authHeader) {
      console.error('❌ 没有找到Authorization头');
      return NextResponse.json({ error: '未授权访问' }, { status: 401 });
    }

    console.log('🔍 调用后端API: POST /api/v1/product-dimensions/templates');
    const response = await backendApi.post(
      '/api/v1/product-dimensions/templates',
      body,
      {
        headers: {
          Authorization: authHeader,
        },
      }
    );
    console.log('🔍 后端API响应成功:', response.status);
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('❌ 创建维度模板失败:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
      stack: error.stack,
    });
    return NextResponse.json(
      { error: '创建维度模板失败', details: error.message },
      { status: error.response?.status || 500 }
    );
  }
}
