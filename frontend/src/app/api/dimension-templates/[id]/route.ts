import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await backendApi.get(
      `/api/v1/product-dimensions/templates/${params.id}`
    );
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('获取维度模板失败:', error);
    return NextResponse.json(
      { error: '获取维度模板失败' },
      { status: error.response?.status || 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const body = await request.json();
    const response = await backendApi.put(
      `/api/v1/product-dimensions/templates/${params.id}`,
      body
    );
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('更新维度模板失败:', error);
    return NextResponse.json(
      { error: '更新维度模板失败' },
      { status: error.response?.status || 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // 从请求头中获取 Authorization token
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return NextResponse.json(
        { error: 'Missing or invalid authorization header' },
        { status: 401 }
      );
    }

    // 调用后端API
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
    const fullUrl = `${backendUrl}/api/v1/product-dimensions/templates/${params.id}`;
    
    const response = await fetch(fullUrl, {
      method: 'DELETE',
      headers: {
        'Authorization': authHeader,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `Backend API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('删除维度模板失败:', error);
    return NextResponse.json(
      { error: '删除维度模板失败', details: error.message },
      { status: error.response?.status || 500 }
    );
  }
}
