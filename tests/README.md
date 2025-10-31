# 数据一致性测试使用指南

## 概述
本目录包含GitHub Stars Manager项目的数据一致性测试套件。

## 文件说明
- `data_consistency_tests.py` - 主测试脚本（326行）
- `README.md` - 本说明文件

## 测试内容
1. **事务测试** - 提交、回滚、隔离
2. **并发测试** - 并发写入、读写
3. **数据同步测试** - 校验和一致性
4. **备份恢复测试** - 数据完整性
5. **缓存测试** - 缓存失效机制
6. **增量更新测试** - 自增ID、时间戳
7. **外键测试** - 约束、级联删除
8. **数据校验测试** - 非空、唯一性、类型

## 环境要求
```bash
uv pip install psycopg2-binary
```

## 配置数据库
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=github_stars_manager
export DB_USER=postgres
export DB_PASSWORD=your_password
```

## 运行测试

### 运行所有测试
```bash
cd /workspace/tests
python data_consistency_tests.py
```

### 运行特定测试类
```bash
python -m unittest data_consistency_tests.TransactionTests
```

### 运行单个测试
```bash
python -m unittest data_consistency_tests.TransactionTests.test_01_commit
```

## 测试输出
- 控制台输出：实时测试结果
- 测试报告：`/workspace/data_consistency_test_report.md`

## 测试结果解读
- `OK` - 所有测试通过
- `FAILED` - 部分测试失败（查看详情）
- `ERROR` - 测试执行错误（通常是环境问题）

## 故障排查
1. 确保PostgreSQL服务运行
2. 检查数据库连接配置
3. 验证表结构是否正确
4. 确认用户权限充足

## 持续集成
建议在CI/CD流程中添加：
```bash
python tests/data_consistency_tests.py || exit 1
```

## 测试频率建议
- 代码变更后：运行完整测试
- 每日构建：自动化测试
- 生产部署前：必须全部通过

## 联系方式
如有问题，请查看详细报告：`data_consistency_test_report.md`
