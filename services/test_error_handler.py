#!/usr/bin/env python3
"""
错误处理工具快速测试脚本
独立运行，不依赖其他模块
"""

import sys
import importlib.util

# 直接加载 error_handler 模块
spec = importlib.util.spec_from_file_location('error_handler', 'error_handler.py')
error_handler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(error_handler)

# 导入需要的类和函数
logger = error_handler.logger
ValidationError = error_handler.ValidationError
AuthenticationError = error_handler.AuthenticationError
NotFoundError = error_handler.NotFoundError
DatabaseError = error_handler.DatabaseError
GitHubAPIError = error_handler.GitHubAPIError
handle_errors = error_handler.handle_errors
retry_on_error = error_handler.retry_on_error
measure_performance = error_handler.measure_performance
ErrorHandler = error_handler.ErrorHandler
CircuitBreaker = error_handler.CircuitBreaker
ErrorCategory = error_handler.ErrorCategory

import time
import random


def test_basic_exceptions():
    """测试基础异常"""
    print("\n" + "=" * 60)
    print("测试 1: 基础异常")
    print("=" * 60)
    
    # 验证错误
    try:
        raise ValidationError("用户名不能为空", field="username")
    except ValidationError as e:
        print(f"✅ ValidationError: {e.message}")
        print(f"   - 错误码: {e.code}")
        print(f"   - 字段: {e.details.get('field')}")
    
    # 认证错误
    try:
        raise AuthenticationError("Token 已过期")
    except AuthenticationError as e:
        print(f"✅ AuthenticationError: {e.message}")
    
    # 资源不存在
    try:
        raise NotFoundError(resource="仓库", resource_id=123)
    except NotFoundError as e:
        print(f"✅ NotFoundError: {e.message}")


def test_decorators():
    """测试装饰器"""
    print("\n" + "=" * 60)
    print("测试 2: 装饰器")
    print("=" * 60)
    
    @handle_errors(error_message="操作失败", category=ErrorCategory.DATABASE)
    def risky_function():
        if random.random() < 0.5:
            raise Exception("随机错误")
        return "成功"
    
    @measure_performance
    def slow_function():
        time.sleep(1)
        return "完成"
    
    # 测试错误处理
    for i in range(3):
        try:
            result = risky_function()
            print(f"  尝试 {i+1}: ✅ {result}")
        except Exception:
            print(f"  尝试 {i+1}: ❌ 失败（已记录）")
    
    # 测试性能监控
    print("\n  执行耗时操作...")
    slow_function()
    print("  ✅ 已记录性能数据")


def test_retry():
    """测试重试机制"""
    print("\n" + "=" * 60)
    print("测试 3: 重试机制")
    print("=" * 60)
    
    attempt_count = [0]
    
    @retry_on_error(max_attempts=3, delay_seconds=0.5, backoff=True)
    def unstable_operation():
        attempt_count[0] += 1
        print(f"  尝试 #{attempt_count[0]}")
        if attempt_count[0] < 3:
            raise ConnectionError("网络错误")
        return "成功"
    
    try:
        result = unstable_operation()
        print(f"✅ 最终结果: {result}")
    except Exception as e:
        print(f"❌ 所有重试失败: {e}")


def test_circuit_breaker():
    """测试熔断器"""
    print("\n" + "=" * 60)
    print("测试 4: 熔断器")
    print("=" * 60)
    
    circuit = CircuitBreaker(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=3,
        name="TestCircuit"
    )
    
    def unstable_api():
        if random.random() < 0.7:
            raise Exception("API 失败")
        return "成功"
    
    print(f"  初始状态: {circuit.state.value}")
    
    for i in range(8):
        try:
            result = circuit.call(unstable_api)
            print(f"  调用 {i+1}: ✅ {result}")
        except Exception as e:
            print(f"  调用 {i+1}: ❌ {type(e).__name__}")
        time.sleep(0.2)
    
    print(f"  最终状态: {circuit.state.value}")
    print(f"  失败次数: {circuit.failure_count}")


def test_error_handler():
    """测试错误处理工具"""
    print("\n" + "=" * 60)
    print("测试 5: 错误处理工具")
    print("=" * 60)
    
    # 测试 GitHub API 错误处理
    print("\n  GitHub API 错误:")
    test_cases = [
        (401, {"message": "Bad credentials"}),
        (403, {"message": "API rate limit exceeded"}),
        (404, {"message": "Not Found"}),
    ]
    
    for status, data in test_cases:
        error = ErrorHandler.handle_github_api_error(status, data)
        print(f"    状态码 {status}: {error.code} - {error.message}")
    
    # 测试数据库错误处理
    print("\n  数据库错误:")
    db_errors = [
        Exception("UNIQUE constraint failed: repos.id"),
        Exception("FOREIGN KEY constraint failed"),
        Exception("NOT NULL constraint failed: repos.name"),
    ]
    
    for err in db_errors:
        db_error = ErrorHandler.handle_database_error(err)
        print(f"    {db_error.message}")


def test_logging():
    """测试日志功能"""
    print("\n" + "=" * 60)
    print("测试 6: 日志功能")
    print("=" * 60)
    
    logger.debug("这是调试信息", user_id=123)
    logger.info("这是信息日志", action="sync_repos")
    logger.warning("这是警告", api_calls=4500)
    logger.error("这是错误", error_code="DB_001")
    
    print("✅ 日志已记录到 logs/ 目录")
    print("  - app_*.log: 所有日志")
    print("  - error_*.log: 仅错误日志")


def main():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("错误处理工具快速测试")
    print("🚀" * 30)
    
    tests = [
        test_basic_exceptions,
        test_decorators,
        test_retry,
        test_circuit_breaker,
        test_error_handler,
        test_logging,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60)
    print("\n📝 提示:")
    print("  1. 查看 logs/ 目录中的日志文件")
    print("  2. 参考 error_handling_guide.md 了解详细用法")
    print("  3. 参考 error_handler_examples.py 查看更多示例")


if __name__ == "__main__":
    main()
