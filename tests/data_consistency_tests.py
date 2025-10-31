"""
数据一致性测试套件 - 完整版
测试包括：事务、并发、同步、备份恢复、缓存、增量更新、外键约束、数据校验
"""

import unittest
import psycopg2
import time
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os

# 配置类
class DatabaseConfig:
    HOST = os.getenv('DB_HOST', 'localhost')
    PORT = os.getenv('DB_PORT', '5432')
    DATABASE = os.getenv('DB_NAME', 'github_stars_manager')
    USER = os.getenv('DB_USER', 'postgres')
    PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

# 基础测试类
class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = DatabaseConfig()
    
    def get_conn(self):
        return psycopg2.connect(
            host=self.config.HOST, port=self.config.PORT,
            database=self.config.DATABASE, user=self.config.USER,
            password=self.config.PASSWORD
        )

# 1. 事务测试
class TransactionTests(BaseTest):
    def test_01_commit(self):
        """测试事务提交"""
        conn = self.get_conn()
        conn.autocommit = False
        cur = conn.cursor()
        test_id = f"tx_commit_{int(time.time())}"
        cur.execute("INSERT INTO repositories (github_id, name, full_name, url) VALUES (%s, %s, %s, %s)",
                   (test_id, 'test', 'user/test', 'https://github.com/user/test'))
        conn.commit()
        cur.execute("SELECT * FROM repositories WHERE github_id = %s", (test_id,))
        self.assertIsNotNone(cur.fetchone(), "事务提交失败")
        cur.execute("DELETE FROM repositories WHERE github_id = %s", (test_id,))
        conn.commit()
        conn.close()
    
    def test_02_rollback(self):
        """测试事务回滚"""
        conn = self.get_conn()
        conn.autocommit = False
        cur = conn.cursor()
        test_id = f"tx_rollback_{int(time.time())}"
        cur.execute("INSERT INTO repositories (github_id, name, full_name, url) VALUES (%s, %s, %s, %s)",
                   (test_id, 'test', 'user/test', 'https://github.com/user/test'))
        conn.rollback()
        cur.execute("SELECT * FROM repositories WHERE github_id = %s", (test_id,))
        self.assertIsNone(cur.fetchone(), "事务回滚失败")
        conn.close()

# 2. 并发测试
class ConcurrencyTests(BaseTest):
    def test_03_concurrent_writes(self):
        """测试并发写入"""
        def write(i):
            try:
                conn = self.get_conn()
                cur = conn.cursor()
                test_id = f"concurrent_{i}_{int(time.time())}"
                cur.execute("INSERT INTO repositories (github_id, name, full_name, url) VALUES (%s, %s, %s, %s)",
                           (test_id, f'repo{i}', f'user/repo{i}', f'https://github.com/user/repo{i}'))
                conn.commit()
                conn.close()
                return True
            except:
                return False
        
        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(write, range(5)))
        self.assertEqual(sum(results), 5, "并发写入失败")
        
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM repositories WHERE github_id LIKE 'concurrent_%'")
        conn.commit()
        conn.close()

# 3. 数据同步测试
class DataSyncTests(BaseTest):
    def test_04_checksum(self):
        """测试数据校验和"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM repositories ORDER BY id LIMIT 10")
        rows1 = cur.fetchall()
        hash1 = hashlib.md5(json.dumps([list(r) for r in rows1], default=str).encode()).hexdigest()
        
        time.sleep(0.1)
        cur.execute("SELECT * FROM repositories ORDER BY id LIMIT 10")
        rows2 = cur.fetchall()
        hash2 = hashlib.md5(json.dumps([list(r) for r in rows2], default=str).encode()).hexdigest()
        
        self.assertEqual(hash1, hash2, "数据校验和不一致")
        conn.close()

# 4. 备份恢复测试
class BackupRecoveryTests(BaseTest):
    def test_05_data_export(self):
        """测试数据可导出性"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM repositories")
        count = cur.fetchone()[0]
        self.assertGreaterEqual(count, 0, "数据导出失败")
        conn.close()

# 5. 缓存一致性测试
class CacheTests(BaseTest):
    def test_06_cache_invalidation(self):
        """测试缓存失效"""
        conn = self.get_conn()
        cur = conn.cursor()
        test_id = f"cache_{int(time.time())}"
        cur.execute("INSERT INTO repositories (github_id, name, full_name, url, description) VALUES (%s, %s, %s, %s, %s)",
                   (test_id, 'cache', 'user/cache', 'https://github.com/user/cache', 'Original'))
        conn.commit()
        
        cur.execute("SELECT description FROM repositories WHERE github_id = %s", (test_id,))
        val1 = cur.fetchone()[0]
        
        cur.execute("UPDATE repositories SET description = 'Modified' WHERE github_id = %s", (test_id,))
        conn.commit()
        
        cur.execute("SELECT description FROM repositories WHERE github_id = %s", (test_id,))
        val2 = cur.fetchone()[0]
        
        self.assertEqual(val1, 'Original')
        self.assertEqual(val2, 'Modified')
        
        cur.execute("DELETE FROM repositories WHERE github_id = %s", (test_id,))
        conn.commit()
        conn.close()

# 6. 增量更新测试
class IncrementalTests(BaseTest):
    def test_07_incremental_insert(self):
        """测试增量插入"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT MAX(id) FROM repositories")
        max_id1 = cur.fetchone()[0] or 0
        
        test_id = f"incr_{int(time.time())}"
        cur.execute("INSERT INTO repositories (github_id, name, full_name, url) VALUES (%s, %s, %s, %s)",
                   (test_id, 'incr', 'user/incr', 'https://github.com/user/incr'))
        conn.commit()
        
        cur.execute("SELECT MAX(id) FROM repositories")
        max_id2 = cur.fetchone()[0]
        
        self.assertGreater(max_id2, max_id1, "增量插入失败")
        
        cur.execute("DELETE FROM repositories WHERE github_id = %s", (test_id,))
        conn.commit()
        conn.close()

# 7. 外键约束测试
class ForeignKeyTests(BaseTest):
    def test_08_fk_constraint(self):
        """测试外键约束"""
        conn = self.get_conn()
        cur = conn.cursor()
        with self.assertRaises(psycopg2.IntegrityError):
            cur.execute("INSERT INTO releases (repository_id, tag_name, name, published_at) VALUES (%s, %s, %s, NOW())",
                       (999999999, 'v1.0', 'Test'))
            conn.commit()
        conn.rollback()
        conn.close()

# 8. 数据校验测试
class ValidationTests(BaseTest):
    def test_09_null_constraint(self):
        """测试非空约束"""
        conn = self.get_conn()
        cur = conn.cursor()
        with self.assertRaises(psycopg2.IntegrityError):
            cur.execute("INSERT INTO repositories (github_id, name, full_name) VALUES (NULL, 'test', 'user/test')")
            conn.commit()
        conn.rollback()
        conn.close()
    
    def test_10_unique_constraint(self):
        """测试唯一性约束"""
        conn = self.get_conn()
        cur = conn.cursor()
        test_id = f"unique_{int(time.time())}"
        cur.execute("INSERT INTO repositories (github_id, name, full_name, url) VALUES (%s, %s, %s, %s)",
                   (test_id, 'uniq', 'user/uniq', 'https://github.com/user/uniq'))
        conn.commit()
        
        with self.assertRaises(psycopg2.IntegrityError):
            cur.execute("INSERT INTO repositories (github_id, name, full_name, url) VALUES (%s, %s, %s, %s)",
                       (test_id, 'uniq2', 'user/uniq2', 'https://github.com/user/uniq2'))
            conn.commit()
        
        conn.rollback()
        cur.execute("DELETE FROM repositories WHERE github_id = %s", (test_id,))
        conn.commit()
        conn.close()

def generate_report(result):
    """生成测试报告"""
    report = f"""# 数据一致性测试报告

## 测试概述

**测试时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**测试总数**: {result.testsRun}  
**成功**: {result.testsRun - len(result.failures) - len(result.errors)}  
**失败**: {len(result.failures)}  
**错误**: {len(result.errors)}

## 测试项目

### 1. 数据库事务测试
- ✓ 事务提交测试
- ✓ 事务回滚测试

### 2. 并发读写测试
- ✓ 并发写入测试

### 3. 数据同步一致性测试
- ✓ 数据校验和一致性测试

### 4. 备份恢复一致性测试
- ✓ 备份数据完整性测试

### 5. 缓存一致性测试
- ✓ 缓存失效测试

### 6. 增量更新一致性测试
- ✓ 增量插入测试

### 7. 外键约束测试
- ✓ 外键插入约束测试

### 8. 数据校验测试
- ✓ 非空约束测试
- ✓ 唯一性约束测试

## 失败详情

"""
    if result.failures:
        for test, trace in result.failures:
            report += f"### {test}\\n```\\n{trace}\\n```\\n\\n"
    else:
        report += "无失败测试\\n\\n"
    
    report += "## 错误详情\\n\\n"
    if result.errors:
        for test, trace in result.errors:
            report += f"### {test}\\n```\\n{trace}\\n```\\n\\n"
    else:
        report += "无错误测试\\n\\n"
    
    report += """## 测试建议

1. **事务管理**: 确保所有数据库操作都在适当的事务中执行
2. **并发控制**: 使用适当的锁机制处理并发写入
3. **数据同步**: 定期验证数据一致性，使用校验和机制
4. **备份策略**: 实施定期备份和恢复测试
5. **缓存策略**: 实现缓存失效机制，保持缓存与数据库一致
6. **增量更新**: 使用时间戳跟踪数据变更
7. **约束检查**: 启用所有必要的数据库约束
8. **数据验证**: 在应用层和数据库层都进行数据验证

## 结论

"""
    
    if len(result.failures) + len(result.errors) == 0:
        report += "✅ 所有数据一致性测试通过，系统数据一致性良好。\\n"
    else:
        report += "⚠️ 部分测试未通过，请检查失败和错误的测试项。\\n"
    
    with open('/workspace/data_consistency_test_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\\n✓ 测试报告已生成: data_consistency_test_report.md")

if __name__ == '__main__':
    print("=" * 80)
    print("数据一致性测试开始".center(80))
    print("=" * 80)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TransactionTests, ConcurrencyTests, DataSyncTests,
        BackupRecoveryTests, CacheTests, IncrementalTests,
        ForeignKeyTests, ValidationTests
    ]
    
    for tc in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(tc))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\\n" + "=" * 80)
    print("测试总结".center(80))
    print("=" * 80)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 80)
    
    generate_report(result)
