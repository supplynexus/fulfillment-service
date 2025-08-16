import { NextRequest, NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({ message: 'Test API working' });
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const username = formData.get('username');
    const password = formData.get('password');
    const tenantName = formData.get('tenant_name');
    
    return NextResponse.json({
      message: 'Test POST working',
      data: { username, tenantName, password: '***' }
    });
  } catch (error) {
    console.error('Test API error:', error);
    return NextResponse.json(
      { detail: 'Test API error' },
      { status: 500 }
    );
  }
}
