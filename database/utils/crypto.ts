/**
 * 加密工具类
 * 用于加密存储敏感数据（GitHub Token、API Key、密码等）
 */

import crypto from 'crypto';

export interface EncryptionConfig {
  algorithm: string;
  key: string;
  ivLength: number;
}

export class CryptoUtil {
  private static config: EncryptionConfig = {
    algorithm: 'aes-256-gcm',
    key: process.env.DB_ENCRYPTION_KEY || 'default-key-change-in-production',
    ivLength: 16
  };

  /**
   * 加密数据
   */
  static encrypt(plaintext: string): string {
    try {
      const iv = crypto.randomBytes(this.config.ivLength);
      const cipher = crypto.createCipher(this.config.algorithm, this.config.key);
      cipher.setAAD(Buffer.from('github-stars-manager'));
      
      let encrypted = cipher.update(plaintext, 'utf8', 'hex');
      encrypted += cipher.final('hex');
      
      const authTag = cipher.getAuthTag();
      
      // 返回格式: iv:authTag:encrypted
      return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;
    } catch (error) {
      throw new Error(`加密失败: ${error.message}`);
    }
  }

  /**
   * 解密数据
   */
  static decrypt(encryptedText: string): string {
    try {
      const parts = encryptedText.split(':');
      if (parts.length !== 3) {
        throw new Error('无效的加密格式');
      }

      const iv = Buffer.from(parts[0], 'hex');
      const authTag = Buffer.from(parts[1], 'hex');
      const encrypted = parts[2];

      const decipher = crypto.createDecipher(this.config.algorithm, this.config.key);
      decipher.setAAD(Buffer.from('github-stars-manager'));
      decipher.setAuthTag(authTag);

      let decrypted = decipher.update(encrypted, 'hex', 'utf8');
      decrypted += decipher.final('utf8');

      return decrypted;
    } catch (error) {
      throw new Error(`解密失败: ${error.message}`);
    }
  }

  /**
   * 生成安全随机字符串
   */
  static generateSecureToken(length: number = 32): string {
    return crypto.randomBytes(length).toString('hex');
  }

  /**
   * SHA256 哈希
   */
  static sha256(data: string): string {
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  /**
   * HMAC-SHA256
   */
  static hmacSHA256(data: string, secret: string): string {
    return crypto.createHmac('sha256', secret).update(data).digest('hex');
  }

  /**
   * 设置加密密钥
   */
  static setEncryptionKey(key: string): void {
    this.config.key = key;
  }

  /**
   * 验证加密配置
   */
  static validateConfig(): boolean {
    return this.config.key.length >= 32 && this.config.algorithm === 'aes-256-gcm';
  }
}
