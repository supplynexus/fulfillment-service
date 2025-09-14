import crypto from 'crypto';

/**
 * 生成后端签名
 * @param privateKey 私钥
 * @param signatureString 签名字符串
 * @param timestamp 时间戳
 * @param nonce 随机数
 * @param tenantName 租户名称
 * @returns 签名
 */
export function generateBackendSignature(
  privateKey: string,
  signatureString: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _timestamp: number,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _nonce: string,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _tenantName: string
): string {
  try {
    // 生成 RSA 签名
    const sign = crypto.createSign('RSA-SHA256');
    sign.update(signatureString);
    const rsaSignature = sign.sign(privateKey, 'base64');

    // 直接返回 RSA 签名，不包装在 JSON 中
    return rsaSignature;
  } catch (error) {
    console.error('Backend signature generation failed', {
      error: String(error),
    });
    throw new Error('Failed to generate backend signature');
  }
}
