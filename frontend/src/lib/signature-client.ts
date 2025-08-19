/**
 * Client-side signature utilities for API authentication
 * 客户端API认证签名工具
 */

export interface SignatureData {
  timestamp: number;
  nonce: string;
  user_id?: number;
  signature: string;
  key_id: string;
}

export interface SignatureOptions {
  method: string;
  path: string;
  body?: string;
  user_id?: number;
  timestamp?: number;
  nonce?: string;
  key_id?: string;
}

/**
 * Get tenant hashid from environment
 * 从环境变量获取租户hashid
 */
export function getTenantHashid(): string {
  return process.env.NEXT_PUBLIC_TENANT_HASHID || 'PoRpOk2e';
}

/**
 * Generate headers for API request (client-side)
 * 为API请求生成认证头（客户端）
 */
export function generateClientHeaders(
  signature: string
): Record<string, string> {
  return {
    'X-Signature': signature,
    'X-Tenant-ID': getTenantHashid(),
    'Content-Type': 'application/json',
  };
}

/**
 * Generate curl command for testing
 * 生成用于测试的curl命令
 */
export function generateCurlCommand(
  method: string = 'GET',
  path: string = '/api/v1/orders',
  signature: string,
  body: string = ''
): string {
  const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${path}`;

  let curl = `curl -X ${method.toUpperCase()} '${url}' \\\n`;
  curl += `  -H 'X-Tenant-ID: ${getTenantHashid()}' \\\n`;
  curl += `  -H 'X-Signature: ${signature}'`;

  if (body && method.toUpperCase() !== 'GET') {
    curl += ` \\\n  -H 'Content-Type: application/json' \\\n`;
    curl += `  -d '${body}'`;
  }

  return curl;
}
