import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const logData = await request.json();
    const timestamp = new Date().toISOString();
    const level = logData.level || 'info';
    const message = logData.message || 'No message';
    const data = logData.data || {};

    console.log(
      `[${timestamp}] [${level.toUpperCase()}] [FRONTEND] ${message}`,
      data
    );

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('[FRONTEND LOG ERROR] Failed to process log:', error);
    return NextResponse.json(
      { success: false, error: String(error) },
      { status: 400 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Frontend Log API',
    usage:
      'POST with { level: "info|warn|error", message: "log message", data: {} }',
  });
}
