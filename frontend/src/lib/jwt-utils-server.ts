import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { JWTPayload, JWTHeader } from './jwt-utils';

export class JWTUtilsServer {
  private static instance: JWTUtilsServer;
  private privateKey: string | null = null;
  private publicKey: string | null = null;

  private constructor() {
    this.loadKeys();
  }

  public static getInstance(): JWTUtilsServer {
    if (!JWTUtilsServer.instance) {
      JWTUtilsServer.instance = new JWTUtilsServer();
    }
    return JWTUtilsServer.instance;
  }

  private loadKeys(): void {
    try {
      const privateKeyPath =
        process.env.FRONTEND_JWT_PRIVATE_KEY_PATH ||
        './keys/frontend_jwt_private_key.pem';
      const publicKeyPath =
        process.env.FRONTEND_JWT_PUBLIC_KEY_PATH ||
        './keys/frontend_jwt_public_key.pem';

      // Resolve paths relative to project root
      const projectRoot = process.cwd();
      const resolvedPrivateKeyPath = path.resolve(projectRoot, privateKeyPath);
      const resolvedPublicKeyPath = path.resolve(projectRoot, publicKeyPath);

      this.privateKey = fs.readFileSync(resolvedPrivateKeyPath, 'utf8');
      this.publicKey = fs.readFileSync(resolvedPublicKeyPath, 'utf8');
    } catch (error) {
      console.error('Failed to load JWT keys:', error);
      throw new Error(`Failed to load JWT keys: ${error}`);
    }
  }

  /**
   * Generate JWT token
   */
  public generateToken(
    payload: Omit<JWTPayload, 'exp' | 'iat'>,
    expiresIn: number = 3600
  ): string {
    if (!this.privateKey) {
      throw new Error('Private key not loaded');
    }

    const now = Math.floor(Date.now() / 1000);
    const exp = now + expiresIn;

    const jwtPayload: JWTPayload = {
      ...payload,
      exp,
      iat: now,
    };

    const header: JWTHeader = {
      alg: 'RS256',
      typ: 'JWT',
    };

    // Encode header and payload
    const encodedHeader = this.base64UrlEncode(JSON.stringify(header));
    const encodedPayload = this.base64UrlEncode(JSON.stringify(jwtPayload));

    // Create signature
    const signatureInput = `${encodedHeader}.${encodedPayload}`;
    const signature = this.sign(signatureInput);

    return `${signatureInput}.${signature}`;
  }

  /**
   * Verify JWT token
   */
  public verifyToken(token: string): JWTPayload {
    if (!this.publicKey) {
      throw new Error('Public key not loaded');
    }

    const parts = token.split('.');
    if (parts.length !== 3) {
      throw new Error('Invalid JWT format');
    }

    const [encodedHeader, encodedPayload, signature] = parts;

    // Verify signature
    const signatureInput = `${encodedHeader}.${encodedPayload}`;
    if (!this.verify(signatureInput, signature)) {
      throw new Error('Invalid JWT signature');
    }

    // Decode payload
    const payload = JSON.parse(
      this.base64UrlDecode(encodedPayload)
    ) as JWTPayload;

    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < now) {
      throw new Error('JWT token expired');
    }

    return payload;
  }

  private sign(data: string): string {
    if (!this.privateKey) {
      throw new Error('Private key not loaded');
    }

    const sign = crypto.createSign('RSA-SHA256');
    sign.update(data);
    return this.base64UrlEncode(sign.sign(this.privateKey, 'base64'));
  }

  private verify(data: string, signature: string): boolean {
    if (!this.publicKey) {
      return false;
    }

    try {
      const verify = crypto.createVerify('RSA-SHA256');
      verify.update(data);
      return verify.verify(
        this.publicKey,
        this.base64UrlDecode(signature),
        'base64'
      );
    } catch (error) {
      return false;
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
export const jwtUtilsServer = JWTUtilsServer.getInstance();
