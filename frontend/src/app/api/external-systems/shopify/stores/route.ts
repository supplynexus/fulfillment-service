import { NextRequest, NextResponse } from 'next/server';
import { createLogger } from '@/lib/logger';

const logger = createLogger('api.external-systems.shopify.stores');

export async function GET(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    logger.info('Request started', { 
      method: request.method, 
      url: request.url 
    });

    // Get authorization header from the request
    const authorization = request.headers.get('authorization');
    if (!authorization) {
      logger.error('Missing authorization header');
      return NextResponse.json(
        { error: 'Authorization header required' },
        { status: 401 }
      );
    }

    // Forward the request to the backend
    const backendUrl = `${process.env.BACKEND_API_URL}/api/v1/shopify/stores`;
    
    logger.info('Forwarding request to backend', { backendUrl });

    const backendResponse = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Authorization': authorization,
        'Content-Type': 'application/json',
      },
    });

    const responseData = await backendResponse.json();

    if (!backendResponse.ok) {
      logger.error('Backend request failed', {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: responseData
      });
      
      return NextResponse.json(
        { error: responseData.detail || 'Backend request failed' },
        { status: backendResponse.status }
      );
    }

    const duration = Date.now() - startTime;
    logger.info('Request completed', { 
      method: request.method, 
      url: request.url,
      status: 200,
      duration: `${duration}ms`
    });
    
    return NextResponse.json(responseData);

  } catch (error: any) {
    const duration = Date.now() - startTime;
    logger.error('API request failed', { 
      error: error.message,
      duration: `${duration}ms`
    });
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
