import { NextRequest, NextResponse } from 'next/server';
import { backendApi } from '@/lib/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const response = await backendApi.get(`/api/v1/product-categories/${params.id}`);
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('获取产品分类详情失败:', error);
    return NextResponse.json(
      { error: '获取产品分类详情失败' },
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
    const response = await backendApi.put(`/api/v1/product-categories/${params.id}`, body);
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('更新产品分类失败:', error);
    return NextResponse.json(
      { error: '更新产品分类失败' },
      { status: error.response?.status || 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    await backendApi.delete(`/api/v1/product-categories/${params.id}`);
    return NextResponse.json({ message: '产品分类删除成功' });
  } catch (error: any) {
    console.error('删除产品分类失败:', error);
    return NextResponse.json(
      { error: '删除产品分类失败' },
      { status: error.response?.status || 500 }
    );
  }
}
