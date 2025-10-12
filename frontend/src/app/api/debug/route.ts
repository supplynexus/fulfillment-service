import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    console.log('🔍 Debug API route called');
    console.log('🔍 Request URL:', request.url);
    
    // 测试各个导入
    const results: any = {};
    
    // 测试 logger
    try {
      const { createLogger } = await import('@/lib/logger');
      const logger = createLogger('debug');
      logger.info('Logger test successful');
      results.logger = { success: true };
    } catch (error) {
      console.error('Logger import failed:', error);
      results.logger = { success: false, error: String(error) };
    }
    
    // 测试 keyLoader
    try {
      const { keyLoader } = await import('@/lib/key-loader');
      const keysDir = keyLoader.getKeysDir();
      results.keyLoader = { success: true, keysDir };
    } catch (error) {
      console.error('KeyLoader import failed:', error);
      results.keyLoader = { success: false, error: String(error) };
    }
    
    // 测试 jwtUtilsServer
    try {
      const { jwtUtilsServer } = await import('@/lib/jwt-utils-server');
      results.jwtUtilsServer = { success: true };
    } catch (error) {
      console.error('JWTUtilsServer import failed:', error);
      results.jwtUtilsServer = { success: false, error: String(error) };
    }
    
    // 测试 signature
    try {
      const { generateBackendSignature } = await import('@/lib/signature');
      results.signature = { success: true };
    } catch (error) {
      console.error('Signature import failed:', error);
      results.signature = { success: false, error: String(error) };
    }
    
    return NextResponse.json({
      status: 'success',
      message: 'Debug API route working',
      timestamp: new Date().toISOString(),
      results
    });
  } catch (error) {
    console.error('Debug API route error:', error);
    return NextResponse.json(
      { error: 'Debug API route failed', details: String(error) },
      { status: 500 }
    );
  }
}
