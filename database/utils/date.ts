/**
 * 时间处理工具类
 */

export class DateUtil {
  /**
   * 获取当前时间戳（秒）
   */
  static now(): number {
    return Math.floor(Date.now() / 1000);
  }

  /**
   * 获取当前时间戳（毫秒）
   */
  static nowMs(): number {
    return Date.now();
  }

  /**
   * 格式化日期为 SQLite DATETIME 格式
   */
  static formatForSQLite(date: Date = new Date()): string {
    return date.toISOString().replace('T', ' ').slice(0, 19);
  }

  /**
   * 解析 SQLite DATETIME 格式
   */
  static parseFromSQLite(datetimeStr: string): Date {
    // SQLite DATETIME format: 'YYYY-MM-DD HH:MM:SS'
    // Replace space with T for ISO format
    return new Date(datetimeStr.replace(' ', 'T') + 'Z');
  }

  /**
   * 获取日期的开始时间（00:00:00）
   */
  static startOfDay(date: Date = new Date()): Date {
    const result = new Date(date);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  /**
   * 获取日期的结束时间（23:59:59）
   */
  static endOfDay(date: Date = new Date()): Date {
    const result = new Date(date);
    result.setHours(23, 59, 59, 999);
    return result;
  }

  /**
   * 获取本周的开始时间（周一 00:00:00）
   */
  static startOfWeek(date: Date = new Date()): Date {
    const result = new Date(date);
    const dayOfWeek = result.getDay();
    const daysToSubtract = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // 周一为一周开始
    result.setDate(result.getDate() - daysToSubtract);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  /**
   * 获取本月的开始时间
   */
  static startOfMonth(date: Date = new Date()): Date {
    const result = new Date(date.getFullYear(), date.getMonth(), 1);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  /**
   * 获取本年的开始时间
   */
  static startOfYear(date: Date = new Date()): Date {
    const result = new Date(date.getFullYear(), 0, 1);
    result.setHours(0, 0, 0, 0);
    return result;
  }

  /**
   * 计算日期差（天数）
   */
  static daysBetween(date1: Date, date2: Date): number {
    const timeDiff = date2.getTime() - date1.getTime();
    return Math.floor(timeDiff / (1000 * 60 * 60 * 24));
  }

  /**
   * 计算日期差（小时）
   */
  static hoursBetween(date1: Date, date2: Date): number {
    const timeDiff = date2.getTime() - date1.getTime();
    return Math.floor(timeDiff / (1000 * 60 * 60));
  }

  /**
   * 计算相对时间描述
   */
  static getRelativeTime(date: Date): string {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) {
      return '刚刚';
    } else if (diffInSeconds < 3600) {
      const minutes = Math.floor(diffInSeconds / 60);
      return `${minutes}分钟前`;
    } else if (diffInSeconds < 86400) {
      const hours = Math.floor(diffInSeconds / 3600);
      return `${hours}小时前`;
    } else if (diffInSeconds < 2592000) {
      const days = Math.floor(diffInSeconds / 86400);
      return `${days}天前`;
    } else if (diffInSeconds < 31536000) {
      const months = Math.floor(diffInSeconds / 2592000);
      return `${months}个月前`;
    } else {
      const years = Math.floor(diffInSeconds / 31536000);
      return `${years}年前`;
    }
  }

  /**
   * 检查是否为同一天
   */
  static isSameDay(date1: Date, date2: Date): boolean {
    return (
      date1.getFullYear() === date2.getFullYear() &&
      date1.getMonth() === date2.getMonth() &&
      date1.getDate() === date2.getDate()
    );
  }

  /**
   * 检查是否为同月
   */
  static isSameMonth(date1: Date, date2: Date): boolean {
    return (
      date1.getFullYear() === date2.getFullYear() &&
      date1.getMonth() === date2.getMonth()
    );
  }

  /**
   * 检查是否为同一年
   */
  static isSameYear(date1: Date, date2: Date): boolean {
    return date1.getFullYear() === date2.getFullYear();
  }

  /**
   * 转换为友好的日期字符串
   */
  static toFriendlyDate(date: Date, showTime: boolean = true): string {
    const now = new Date();
    const isToday = this.isSameDay(date, now);
    const isThisYear = this.isSameYear(date, now);

    if (isToday && showTime) {
      return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      });
    }

    if (isThisYear) {
      return date.toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric'
      });
    }

    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  /**
   * 验证日期有效性
   */
  static isValidDate(date: any): boolean {
    return date instanceof Date && !isNaN(date.getTime());
  }

  /**
   * 安全解析日期
   */
  static safeParse(dateStr: string): Date | null {
    try {
      const date = new Date(dateStr);
      return this.isValidDate(date) ? date : null;
    } catch {
      return null;
    }
  }

  /**
   * 获取时区偏移量（小时）
   */
  static getTimezoneOffset(): number {
    return new Date().getTimezoneOffset() / 60;
  }

  /**
   * UTC 时间戳转换为本地时间
   */
  static utcToLocal(utcTimestamp: number): Date {
    return new Date(utcTimestamp * 1000);
  }

  /**
   * 本地时间转换为 UTC 时间戳
   */
  static localToUTC(date: Date): number {
    return Math.floor(date.getTime() / 1000);
  }
}
