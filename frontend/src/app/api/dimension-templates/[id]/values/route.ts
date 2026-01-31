import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await backendApi.get(
      `/api/v1/product-dimensions/templates/${params.id}/values`
    );
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('获取维度值列表失败:', error);
    return NextResponse.json(
      { error: '获取维度值列表失败' },
      { status: error.response?.status || 500 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const body = await request.json();
    const response = await backendApi.post(
      `/api/v1/product-dimensions/templates/${params.id}/values`,
      body
    );
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('创建维度值失败:', error);
    return NextResponse.json(
      { error: '创建维度值失败' },
      { status: error.response?.status || 500 }
    );
  }
}
