"""
错误处理工具使用示例

演示如何在项目中使用统一的错误处理体系
"""

from services.error_handler import (
    logger,
    ErrorHandler,
    handle_errors,
    retry_on_error,
    measure_performance,
    CircuitBreaker,
    ValidationError,
    AuthenticationError,
    NotFoundError,
    DatabaseError,
    GitHubAPIError,
    ErrorCategory,
    error_reporter,
)
import time
import random


# ============================================================================
# 示例 1: 基础错误处理
# ============================================================================

def example_basic_error_handling():
    """基础错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 1: 基础错误处理")
    print("=" * 60)
    
    # 抛出验证错误
    try:
        token = ""
        if not token:
            raise ValidationError("GitHub Token 不能为空", field="token")
    except ValidationError as e:
        logger.error(f"验证失败: {e.message}", field=e.details.get('field'))
        print(f"❌ 捕获验证错误: {e}")
    
    # 抛出认证错误
    try:
        raise AuthenticationError("Token 已过期")
    except AuthenticationError as e:
        logger.error(f"认证失败: {e.message}")
        print(f"❌ 捕获认证错误: {e}")
    
    # 抛出资源不存在错误
    try:
        repo_id = 12345
        raise NotFoundError(resource="仓库", resource_id=repo_id)
    except NotFoundError as e:
        logger.warning(f"资源未找到: {e.message}", resource_id=e.details.get('resource_id'))
        print(f"⚠️ 捕获资源不存在错误: {e}")


# ============================================================================
# 示例 2: 使用装饰器处理错误
# ============================================================================

@handle_errors(
    error_message="获取仓库列表失败",
    log_error=True,
    category=ErrorCategory.DATABASE
)
def get_repositories():
    """获取仓库列表（带错误处理）"""
    # 模拟数据库查询
    print("  📊 正在查询仓库列表...")
    
    # 模拟错误
    if random.random() < 0.3:
        raise Exception("数据库连接失败")
    
    return [
        {"id": 1, "name": "repo1"},
        {"id": 2, "name": "repo2"},
    ]


def example_decorator_error_handling():
    """装饰器错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 2: 使用装饰器处理错误")
    print("=" * 60)
    
    try:
        repos = get_repositories()
        print(f"✅ 成功获取 {len(repos)} 个仓库")
    except Exception as e:
        print(f"❌ 获取仓库失败: {e}")


# ============================================================================
# 示例 3: 重试机制
# ============================================================================

@retry_on_error(
    max_attempts=3,
    delay_seconds=1,
    backoff=True,
    catch_exceptions=(ConnectionError, TimeoutError)
)
def fetch_github_data():
    """获取 GitHub 数据（带重试）"""
    print("  🌐 正在请求 GitHub API...")
    
    # 模拟网络错误
    if random.random() < 0.6:
        raise ConnectionError("网络连接失败")
    
    return {"user": "test", "repos": 100}


def example_retry_mechanism():
    """重试机制示例"""
    print("\n" + "=" * 60)
    print("示例 3: 重试机制")
    print("=" * 60)
    
    try:
        data = fetch_github_data()
        print(f"✅ 成功获取数据: {data}")
    except Exception as e:
        print(f"❌ 所有重试都失败: {e}")


# ============================================================================
# 示例 4: 性能监控
# ============================================================================

@measure_performance
def process_large_dataset():
    """处理大数据集（带性能监控）"""
    print("  ⚙️ 正在处理数据...")
    time.sleep(2)  # 模拟耗时操作
    return {"processed": 1000}


@measure_performance
def slow_operation():
    """慢操作（会触发警告）"""
    print("  🐌 正在执行慢操作...")
    time.sleep(6)  # 超过 5 秒会触发警告
    return {"status": "completed"}


def example_performance_monitoring():
    """性能监控示例"""
    print("\n" + "=" * 60)
    print("示例 4: 性能监控")
    print("=" * 60)
    
    # 正常操作
    result1 = process_large_dataset()
    print(f"✅ 数据处理完成: {result1}")
    
    # 慢操作
    result2 = slow_operation()
    print(f"⚠️ 慢操作完成: {result2}")


# ============================================================================
# 示例 5: 熔断器模式
# ============================================================================

# 创建熔断器实例
github_circuit = CircuitBreaker(
    failure_threshold=3,
    success_threshold=2,
    timeout_seconds=5,
    name="GitHubAPI"
)


def unstable_api_call():
    """不稳定的 API 调用"""
    # 模拟 70% 失败率
    if random.random() < 0.7:
        raise ConnectionError("API 调用失败")
    return {"status": "success"}


def example_circuit_breaker():
    """熔断器模式示例"""
    print("\n" + "=" * 60)
    print("示例 5: 熔断器模式")
    print("=" * 60)
    
    for i in range(10):
        try:
            result = github_circuit.call(unstable_api_call)
            print(f"  尝试 {i+1}: ✅ 成功 - {result}")
        except Exception as e:
            print(f"  尝试 {i+1}: ❌ 失败 - {type(e).__name__}: {e}")
        
        time.sleep(0.5)
    
    print(f"\n熔断器状态: {github_circuit.state.value}")
    print(f"失败次数: {github_circuit.failure_count}")


# ============================================================================
# 示例 6: GitHub API 错误处理
# ============================================================================

def handle_github_response(status_code: int, response_data: dict):
    """处理 GitHub API 响应"""
    if status_code != 200:
        error = ErrorHandler.handle_github_api_error(status_code, response_data)
        logger.log_exception(error)
        raise error
    
    return response_data


def example_github_api_error_handling():
    """GitHub API 错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 6: GitHub API 错误处理")
    print("=" * 60)
    
    # 模拟各种 GitHub API 错误响应
    test_cases = [
        (401, {"message": "Bad credentials"}),
        (403, {"message": "API rate limit exceeded", "reset": int(time.time()) + 3600}),
        (404, {"message": "Not Found"}),
        (500, {"message": "Internal Server Error"}),
    ]
    
    for status_code, response_data in test_cases:
        try:
            handle_github_response(status_code, response_data)
        except Exception as e:
            print(f"  状态码 {status_code}: ❌ {type(e).__name__} - {e.message if hasattr(e, 'message') else e}")


# ============================================================================
# 示例 7: 数据库错误处理
# ============================================================================

def simulate_database_operation(error_type: str = None):
    """模拟数据库操作"""
    if error_type == "unique":
        raise Exception("UNIQUE constraint failed: repositories.github_id")
    elif error_type == "foreign_key":
        raise Exception("FOREIGN KEY constraint failed")
    elif error_type == "not_null":
        raise Exception("NOT NULL constraint failed: repositories.name")
    elif error_type == "no_table":
        raise Exception("no such table: repositories")
    else:
        return {"id": 1, "name": "test_repo"}


def example_database_error_handling():
    """数据库错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 7: 数据库错误处理")
    print("=" * 60)
    
    error_types = ["unique", "foreign_key", "not_null", "no_table", None]
    
    for error_type in error_types:
        try:
            result = simulate_database_operation(error_type)
            print(f"  {error_type or '正常'}: ✅ 操作成功 - {result}")
        except Exception as e:
            db_error = ErrorHandler.handle_database_error(e, query="INSERT INTO repositories ...")
            logger.log_exception(db_error)
            print(f"  {error_type}: ❌ {db_error.message}")


# ============================================================================
# 示例 8: 安全执行
# ============================================================================

def risky_operation():
    """可能失败的操作"""
    if random.random() < 0.5:
        raise ValueError("操作失败")
    return "成功结果"


def example_safe_execute():
    """安全执行示例"""
    print("\n" + "=" * 60)
    print("示例 8: 安全执行")
    print("=" * 60)
    
    for i in range(5):
        result = ErrorHandler.safe_execute(
            operation=risky_operation,
            default_value="默认值",
            error_message=f"尝试 {i+1} 失败"
        )
        print(f"  尝试 {i+1}: 结果 = {result}")


# ============================================================================
# 示例 9: 错误统计
# ============================================================================

def example_error_statistics():
    """错误统计示例"""
    print("\n" + "=" * 60)
    print("示例 9: 错误统计")
    print("=" * 60)
    
    # 模拟一些错误
    errors = [
        ValidationError("无效的输入", field="name"),
        AuthenticationError("Token 无效"),
        NotFoundError("仓库", resource_id=123),
        DatabaseError("查询失败", query="SELECT * FROM repos"),
        GitHubAPIError("API 调用失败", status_code=500),
    ]
    
    # 上报错误
    for error in errors:
        error_reporter.report(error, context={"user_id": "test_user"})
    
    # 获取统计
    stats = error_reporter.get_error_statistics()
    print(f"\n错误统计:")
    print(f"  总计: {stats['total']}")
    print(f"  按分类:")
    for category, count in stats['by_category'].items():
        print(f"    - {category}: {count}")
    print(f"  按错误码:")
    for code, count in stats['by_code'].items():
        print(f"    - {code}: {count}")


# ============================================================================
# 示例 10: 综合应用
# ============================================================================

class RepositoryService:
    """仓库服务（综合示例）"""
    
    def __init__(self):
        self.circuit = CircuitBreaker(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=10,
            name="RepositoryService"
        )
    
    @handle_errors(
        error_message="同步仓库失败",
        category=ErrorCategory.SYNC
    )
    @retry_on_error(max_attempts=3, delay_seconds=2, backoff=True)
    @measure_performance
    def sync_repositories(self, token: str):
        """同步仓库（综合错误处理）"""
        logger.info("开始同步仓库")
        
        # 验证 token
        if not token or len(token) < 10:
            raise ValidationError("Token 格式不正确", field="token")
        
        # 通过熔断器调用 GitHub API
        def fetch_repos():
            # 模拟 API 调用
            if random.random() < 0.2:
                raise ConnectionError("网络连接失败")
            return [{"id": 1, "name": "repo1"}, {"id": 2, "name": "repo2"}]
        
        repos = self.circuit.call(fetch_repos)
        
        # 保存到数据库
        saved_count = 0
        for repo in repos:
            try:
                # 模拟数据库操作
                if random.random() < 0.1:
                    raise Exception("UNIQUE constraint failed")
                saved_count += 1
            except Exception as e:
                db_error = ErrorHandler.handle_database_error(e)
                logger.warning(f"保存仓库失败: {db_error.message}", repo_id=repo['id'])
        
        logger.info(f"同步完成", total=len(repos), saved=saved_count)
        return {"total": len(repos), "saved": saved_count}


def example_comprehensive():
    """综合应用示例"""
    print("\n" + "=" * 60)
    print("示例 10: 综合应用")
    print("=" * 60)
    
    service = RepositoryService()
    
    # 测试 1: 无效 token
    try:
        service.sync_repositories("")
    except Exception as e:
        print(f"  测试 1 (无效token): ❌ {e}")
    
    # 测试 2: 正常同步
    try:
        result = service.sync_repositories("valid_token_123456")
        print(f"  测试 2 (正常同步): ✅ {result}")
    except Exception as e:
        print(f"  测试 2 (正常同步): ❌ {e}")


# ============================================================================
# 运行所有示例
# ============================================================================

def main():
    """运行所有示例"""
    print("\n" + "🚀" * 30)
    print("GitHub Stars Manager - 错误处理示例")
    print("🚀" * 30)
    
    examples = [
        ("基础错误处理", example_basic_error_handling),
        ("装饰器错误处理", example_decorator_error_handling),
        ("重试机制", example_retry_mechanism),
        ("性能监控", example_performance_monitoring),
        ("熔断器模式", example_circuit_breaker),
        ("GitHub API 错误处理", example_github_api_error_handling),
        ("数据库错误处理", example_database_error_handling),
        ("安全执行", example_safe_execute),
        ("错误统计", example_error_statistics),
        ("综合应用", example_comprehensive),
    ]
    
    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n❌ 示例 '{name}' 执行失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 所有示例执行完成!")
    print("=" * 60)
    print("\n📝 提示:")
    print("  - 检查 logs/ 目录查看详细日志")
    print("  - 错误日志单独记录在 error_*.log 文件中")
    print("  - 可以根据需要调整日志级别和输出格式")


if __name__ == "__main__":
    main()
