# Docker Secrets 配置指南

## 📋 概述

Docker Secrets 是一种安全管理敏感信息（如密码、密钥、证书）的方式。本项目使用 file-based secrets 来管理敏感配置。

## 🔐 创建密钥

### 1. 创建密钥目录

```bash
cd Docker
mkdir -p secrets
chmod 700 secrets
```

### 2. 生成密钥文件

#### 数据库密码
```bash
# 使用强随机密码
openssl rand -base64 32 > secrets/db_password.txt

# 或手动设置
echo "your_secure_db_password_here" > secrets/db_password.txt
```

#### Redis 密码
```bash
# 生成 Redis 密码
openssl rand -base64 32 > secrets/redis_password.txt

# 或手动设置
echo "your_secure_redis_password_here" > secrets/redis_password.txt
```

#### JWT Secret
```bash
# 生成 JWT 密钥（64 字符十六进制）
openssl rand -hex 32 > secrets/jwt_secret.txt
```

### 3. 设置正确的权限

```bash
# 设置密钥文件权限（仅所有者可读写）
chmod 600 secrets/*.txt

# 验证权限
ls -la secrets/
# 应该显示: -rw------- (600)
```

## 📁 目录结构

```
Docker/
├── secrets/
│   ├── db_password.txt      # PostgreSQL 密码
│   ├── redis_password.txt   # Redis 密码
│   └── jwt_secret.txt       # JWT 签名密钥
├── .env                      # 环境变量
└── docker-compose.optimized.yml
```

## 🔧 在容器中使用 Secrets

### 配置示例

```yaml
services:
  backend:
    secrets:
      - db_password
      - redis_password
      - jwt_secret
    environment:
      - DB_PASSWORD_FILE=/run/secrets/db_password
      - REDIS_PASSWORD_FILE=/run/secrets/redis_password
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
```

### 读取 Secret（Node.js 示例）

```javascript
const fs = require('fs');

// 读取密码
function getSecret(secretPath) {
  try {
    return fs.readFileSync(secretPath, 'utf8').trim();
  } catch (error) {
    console.error(`Failed to read secret: ${secretPath}`, error);
    throw error;
  }
}

// 使用示例
const dbPassword = getSecret('/run/secrets/db_password');
const redisPassword = getSecret('/run/secrets/redis_password');
const jwtSecret = getSecret('/run/secrets/jwt_secret');

// 数据库配置
const dbConfig = {
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: dbPassword
};
```

## 🔄 密钥轮换

### 1. 生成新密钥

```bash
# 备份旧密钥
cp secrets/db_password.txt secrets/db_password.txt.backup

# 生成新密钥
openssl rand -base64 32 > secrets/db_password.txt
```

### 2. 更新数据库密码

```bash
# 连接到数据库容器
docker-compose -f docker-compose.optimized.yml exec postgres psql -U app_user

# 更新密码
ALTER USER app_user WITH PASSWORD 'new_password_here';
\q
```

### 3. 重启服务

```bash
docker-compose -f docker-compose.optimized.yml restart backend
```

## ⚠️ 安全最佳实践

### 1. 密钥强度

- **最小长度**: 32 字符
- **字符集**: 大小写字母、数字、特殊字符
- **避免**: 字典单词、个人信息、常见密码

### 2. 权限管理

```bash
# 密钥目录权限
chmod 700 secrets/

# 密钥文件权限
chmod 600 secrets/*.txt

# 验证没有组和其他用户权限
ls -la secrets/
# 输出: drwx------ (目录)
#       -rw------- (文件)
```

### 3. 版本控制

**永远不要提交密钥到版本控制！**

```bash
# .gitignore
secrets/
*.txt
.env
```

### 4. 备份管理

```bash
# 创建加密备份
tar czf secrets-backup.tar.gz secrets/
gpg --symmetric --cipher-algo AES256 secrets-backup.tar.gz

# 安全存储加密文件
mv secrets-backup.tar.gz.gpg /secure/backup/location/

# 清理明文备份
rm secrets-backup.tar.gz
```

## 🔍 验证配置

### 1. 检查密钥文件

```bash
# 验证文件存在
ls -la secrets/

# 验证文件不为空
for file in secrets/*.txt; do
  if [ ! -s "$file" ]; then
    echo "Warning: $file is empty"
  fi
done
```

### 2. 测试密钥读取

```bash
# 在容器中验证
docker-compose -f docker-compose.optimized.yml exec backend sh -c '
  if [ -f /run/secrets/db_password ]; then
    echo "✓ db_password accessible"
  else
    echo "✗ db_password not found"
  fi
'
```

### 3. 验证数据库连接

```bash
# 测试数据库连接
docker-compose -f docker-compose.optimized.yml exec backend node -e "
const fs = require('fs');
const { Client } = require('pg');

const password = fs.readFileSync('/run/secrets/db_password', 'utf8').trim();

const client = new Client({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: password
});

client.connect()
  .then(() => {
    console.log('✓ Database connection successful');
    return client.end();
  })
  .catch(err => {
    console.error('✗ Database connection failed:', err.message);
    process.exit(1);
  });
"
```

## 🚨 故障排除

### 问题 1: Permission denied

```bash
# 症状
Error: EACCES: permission denied, open '/run/secrets/db_password'

# 解决方案
chmod 600 secrets/db_password.txt
```

### 问题 2: Secret not found

```bash
# 症状
Error: ENOENT: no such file or directory, open '/run/secrets/db_password'

# 检查
docker-compose -f docker-compose.optimized.yml config | grep secrets

# 确保 secrets 在服务中正确配置
```

### 问题 3: Empty secret

```bash
# 症状
Database connection failed: password authentication failed

# 检查密钥文件
cat secrets/db_password.txt

# 重新生成密钥
openssl rand -base64 32 > secrets/db_password.txt
```

## 📚 密钥清单

创建一个密钥清单文件（不包含实际密钥值）：

```bash
# secrets/README.md
# 密钥文件清单

## 必需的密钥文件

- [ ] db_password.txt - PostgreSQL 数据库密码
- [ ] redis_password.txt - Redis 缓存密码
- [ ] jwt_secret.txt - JWT 签名密钥

## 可选的密钥文件

- [ ] ssl_cert.pem - SSL 证书
- [ ] ssl_key.pem - SSL 私钥
- [ ] api_key.txt - 第三方 API 密钥

## 密钥生成命令

### 数据库密码
openssl rand -base64 32 > db_password.txt

### Redis 密码
openssl rand -base64 32 > redis_password.txt

### JWT 密钥
openssl rand -hex 32 > jwt_secret.txt

## 最后更新
- 创建日期: YYYY-MM-DD
- 更新日期: YYYY-MM-DD
- 下次轮换: YYYY-MM-DD (建议每90天)
```

## 🔐 生产环境建议

### 1. 使用专业密钥管理系统

生产环境建议使用：
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault
- Google Secret Manager

### 2. 定期轮换密钥

```bash
# 设置提醒
echo "0 0 1 */3 * /path/to/rotate-secrets.sh" | crontab -
```

### 3. 审计日志

记录密钥访问和修改：

```bash
# 记录密钥访问
docker-compose -f docker-compose.optimized.yml logs backend | grep -i "secret\|password"
```

### 4. 多因素认证

对访问密钥文件的操作启用 MFA：
- SSH 密钥 + 密码
- VPN + 2FA
- 堡垒机访问

## 📖 参考资料

- [Docker Secrets 文档](https://docs.docker.com/engine/swarm/secrets/)
- [OWASP 密钥管理最佳实践](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)
- [NIST 密钥管理指南](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)

## ✅ 初始化检查清单

使用此清单确保正确设置：

- [ ] 创建 `secrets/` 目录
- [ ] 设置目录权限 `700`
- [ ] 生成所有必需的密钥文件
- [ ] 设置文件权限 `600`
- [ ] 验证密钥文件不为空
- [ ] 将 `secrets/` 添加到 `.gitignore`
- [ ] 创建加密备份
- [ ] 测试容器内密钥访问
- [ ] 验证应用程序可以读取密钥
- [ ] 文档记录密钥轮换计划

---

**安全提醒**: 密钥管理是系统安全的关键。定期审查和更新密钥，遵循最小权限原则。
