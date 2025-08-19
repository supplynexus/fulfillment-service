import crypto from 'crypto';

export interface JWTPayload {
  sub: string; // User ID
  tenant_id: number; // Tenant ID
  email: string; // User email
  tenant_name: string; // Tenant name
  exp: number; // Expiration time
  iat: number; // Issued at time
  type: 'access' | 'refresh';
}

export interface JWTHeader {
  alg: 'RS256';
  typ: 'JWT';
}

export class JWTUtils {
  private static instance: JWTUtils;

  private constructor() {}

  public static getInstance(): JWTUtils {
    if (!JWTUtils.instance) {
      JWTUtils.instance = new JWTUtils();
    }
    return JWTUtils.instance;
  }

  /**
   * Decode JWT token without verification (client-side safe)
   */
  public decodeToken(token: string): JWTPayload {
    const parts = token.split('.');
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format');
    }

    const [, encodedPayload] = parts;
    return JSON.parse(this.base64UrlDecode(encodedPayload));
  }

  /**
   * Check if JWT token is expired (client-side safe)
   */
  public isTokenExpired(token: string): boolean {
    try {
      const payload = this.decodeToken(token);
      const now = Math.floor(Date.now() / 1000);
      return payload.exp < now;
    } catch (error) {
      return true;
    }
  }

  /**
   * Check if JWT token is expiring soon (client-side safe)
   */
  public isTokenExpiringSoon(
    token: string,
    bufferMinutes: number = 5
  ): boolean {
    try {
      const payload = this.decodeToken(token);
      const now = Math.floor(Date.now() / 1000);
      const bufferSeconds = bufferMinutes * 60;
      return payload.exp - now <= bufferSeconds;
    } catch (error) {
      return true;
    }
  }

  private base64UrlEncode(str: string): string {
    return Buffer.from(str)
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  private base64UrlDecode(str: string): string {
    // Add padding back
    str += '='.repeat((4 - (str.length % 4)) % 4);
    str = str.replace(/-/g, '+').replace(/_/g, '/');
    return Buffer.from(str, 'base64').toString('utf8');
  }
}

// Export singleton instance
export const jwtUtils = JWTUtils.getInstance();
