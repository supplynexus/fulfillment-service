import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await backendApi.get(`/api/v1/product-variants/${params.id}`);
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('获取产品变体详情失败:', error);
    return NextResponse.json(
      { error: '获取产品变体详情失败' },
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
    const response = await backendApi.put(`/api/v1/product-variants/${params.id}`, body);
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('更新产品变体失败:', error);
    return NextResponse.json(
      { error: '更新产品变体失败' },
      { status: error.response?.status || 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await backendApi.delete(`/api/v1/product-variants/${params.id}`);
    return NextResponse.json({ message: '产品变体删除成功' });
  } catch (error: any) {
    console.error('删除产品变体失败:', error);
    return NextResponse.json(
      { error: '删除产品变体失败' },
      { status: error.response?.status || 500 }
    );
  }
}
