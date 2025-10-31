/**
 * 基础 DAO 异常类
 */

export class DAOException extends Error {
  constructor(
    message: string,
    public code?: string,
    public cause?: Error
  ) {
    super(message);
    this.name = 'DAOException';
  }
}
