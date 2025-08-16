import { NextRequest, NextResponse } from 'next/server';
import { setRequestId, generateRequestId } from '@/lib/logger';

export function middleware(request: NextRequest) {
  // 只为API路由生成请求ID
  if (request.nextUrl.pathname.startsWith('/api/')) {
    const requestId = generateRequestId();
    setRequestId(requestId);
    
    // 在响应头中添加请求ID
    const response = NextResponse.next();
    response.headers.set('X-Request-ID', requestId);
    
    return response;
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: '/api/:path*',
};
