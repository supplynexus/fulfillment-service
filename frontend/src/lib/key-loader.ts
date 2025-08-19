import fs from 'fs';
import path from 'path';

/**
 * 密钥加载器 - 从文件系统加载私钥
 */
export class KeyLoader {
  private static instance: KeyLoader;
  private keysDir: string;
  private keyCache: Map<string, string> = new Map();

  // 租户ID映射
  private tenantIds: Record<string, number> = {
    impeach: 1,
    // 添加更多租户的 ID
  };

  private constructor() {
    // 密钥文件目录
    this.keysDir = path.join(process.cwd(), 'keys');
  }

  static getInstance(): KeyLoader {
    if (!KeyLoader.instance) {
      KeyLoader.instance = new KeyLoader();
    }
    return KeyLoader.instance;
  }

  /**
   * 获取租户ID
   * @param tenantName 租户名称
   * @returns 租户ID
   */
  async getTenantId(tenantName: string): Promise<number> {
    const tenantId = this.tenantIds[tenantName];
    if (!tenantId) {
      throw new Error(`Tenant ID not found for tenant: ${tenantName}`);
    }
    return tenantId;
  }

  /**
   * 获取租户的私钥（异步版本）
   * @param tenantName 租户名称
   * @returns 私钥内容
   */
  async getTenantPrivateKey(tenantName: string): Promise<string> {
    return this.loadTenantPrivateKey(tenantName);
  }

  /**
   * 加载租户的私钥
   * @param tenantName 租户名称
   * @returns 私钥内容
   */
  loadTenantPrivateKey(tenantName: string): string {
    // 检查缓存
    if (this.keyCache.has(tenantName)) {
      return this.keyCache.get(tenantName)!;
    }

    const keyPath = path.join(this.keysDir, `${tenantName}_private_key.pem`);

    try {
      if (!fs.existsSync(keyPath)) {
        throw new Error(`Private key file not found: ${keyPath}`);
      }

      const privateKey = fs.readFileSync(keyPath, 'utf8').trim();

      // 验证私钥格式
      if (!privateKey.includes('-----BEGIN PRIVATE KEY-----')) {
        throw new Error(`Invalid private key format in file: ${keyPath}`);
      }

      // 缓存私钥
      this.keyCache.set(tenantName, privateKey);

      console.log(`✅ Loaded private key for tenant: ${tenantName}`);
      return privateKey;
    } catch (error) {
      console.error(
        `❌ Failed to load private key for tenant ${tenantName}:`,
        error
      );
      throw new Error(
        `Failed to load private key for tenant ${tenantName}: ${error}`
      );
    }
  }

  /**
   * 获取所有可用的租户密钥
   * @returns 租户名称列表
   */
  getAvailableTenants(): string[] {
    try {
      if (!fs.existsSync(this.keysDir)) {
        return [];
      }

      const files = fs.readdirSync(this.keysDir);
      const tenantNames = files
        .filter(file => file.endsWith('_private_key.pem'))
        .map(file => file.replace('_private_key.pem', ''));

      return tenantNames;
    } catch (error) {
      console.error('Failed to get available tenants:', error);
      return [];
    }
  }

  /**
   * 检查租户密钥是否存在
   * @param tenantName 租户名称
   * @returns 是否存在
   */
  hasTenantKey(tenantName: string): boolean {
    const keyPath = path.join(this.keysDir, `${tenantName}_private_key.pem`);
    return fs.existsSync(keyPath);
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.keyCache.clear();
  }

  /**
   * 获取密钥目录路径
   */
  getKeysDir(): string {
    return this.keysDir;
  }
}

// 导出单例实例
export const keyLoader = KeyLoader.getInstance();
