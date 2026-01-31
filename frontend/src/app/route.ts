import { NextRequest, NextResponse } from 'next/server';
import { redirect } from 'next/navigation';

// 处理根路径的所有 HTTP 方法
export async function GET() {
  // GET 请求重定向到登录页
  redirect('/auth/login');
}

export async function POST(request: NextRequest) {
  // POST 请求返回 405 Method Not Allowed
  return NextResponse.json(
    { error: 'Method Not Allowed' },
    { status: 405 }
  );
}

export async function PUT(request: NextRequest) {
  return NextResponse.json(
    { error: 'Method Not Allowed' },
    { status: 405 }
  );
}

export async function DELETE(request: NextRequest) {
  return NextResponse.json(
    { error: 'Method Not Allowed' },
    { status: 405 }
  );
}

export async function PATCH(request: NextRequest) {
  return NextResponse.json(
    { error: 'Method Not Allowed' },
    { status: 405 }
  );
}
