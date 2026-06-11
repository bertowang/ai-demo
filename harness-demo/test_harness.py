"""
测试脚本：演示 Harness 的使用（无需真实 API Key）

本脚本使用 mock 模式，模拟 LLM 的响应，
让您可以在没有 API Key 的情况下，理解 Harness 的工作原理。

作者：Berton
日期：2026-06-10
"""

import sys
import os
import inspect

# 确保可以导入 harness.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness import Harness, TOOLS_SCHEMA, TOOL_REGISTRY


def log_print(*args, **kwargs) -> None:
    """
    带行号打印的辅助函数
    
    Args:
        *args: 要打印的内容
        **kwargs: print 函数的其他参数
    """
    # 获取调用者的行号
    caller_frame = inspect.currentframe().f_back
    line_no: int = caller_frame.f_lineno if caller_frame else 0
    filename: str = os.path.basename(caller_frame.f_code.co_filename) if caller_frame else "unknown"
    
    # 在打印内容前添加行号信息
    print(f"[Line {line_no}]", *args, **kwargs)


def test_tool_routing() -> None:
    """
    测试工具路由功能
    """
    log_print("\n" + "=" * 60)
    log_print("  测试 1：工具路由与执行")
    log_print("=" * 60)

    harness = Harness()

    # 模拟 LLM 返回的工具调用
    class MockToolCall:
        def __init__(self, name: str, arguments: str) -> None:
            self.id: str = "call_123"
            self.function = type(
                "Function",
                (),
                {"name": name, "arguments": arguments},
            )()

    # 测试 read_file 工具
    log_print("\n📩 模拟 LLM 调用工具：read_file")
    tool_call = MockToolCall(
        name="read_file",
        arguments='{"path": "/Users/berton/prj/mcp-demo-all/harness-demo/harness.py"}',
    )
    result: str = harness.execute_tool(tool_call)
    # 注意：harness.py 中的 log_step 已经打印了完整结果
    # 这里只验证工具调用是否成功，不重复打印结果
    log_print(f"📩 工具调用成功，返回结果长度：{len(result)} 字符")

    # 测试 calculate 工具
    log_print("\n📩 模拟 LLM 调用工具：calculate")
    tool_call = MockToolCall(
        name="calculate",
        arguments='{"expression": "15 * 37"}',
    )
    result = harness.execute_tool(tool_call)
    log_print(f"📩 工具返回结果：{result}")

    # 测试权限控制（沙箱）
    log_print("\n📩 模拟 LLM 调用工具：read_file（越权访问）")
    tool_call = MockToolCall(
        name="read_file",
        arguments='{"path": "/etc/passwd"}',  # 不在 ALLOWED_DIRS 内
    )
    result = harness.execute_tool(tool_call)
    log_print(f"📩 工具返回结果：{result}")


def test_context_management() -> None:
    """
    测试上下文管理功能
    """
    log_print("\n" + "=" * 60)
    log_print("  测试 2：上下文/记忆管理")
    log_print("=" * 60)

    harness = Harness()

    # 模拟多轮对话的上下文
    harness.conversation_history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你？"},
        {"role": "user", "content": "请读取 /tmp/test.txt"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "call_1", "function": {"name": "read_file", "arguments": '{"path": "/tmp/test.txt"}'}}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "文件内容：Hello World"},
    ]

    log_print(f"\n📊 当前上下文长度：{len(harness.conversation_history)} 条消息")
    log_print("📊 上下文内容（仅显示角色和长度）：")
    for i, msg in enumerate(harness.conversation_history):
        role: str = msg.get("role", "unknown")
        content = msg.get("content", "") or ""
        content_len: int = len(str(content))
        # 只打印角色和内容长度，不打印完整内容
        log_print(f"  {i + 1}. [{role}] 内容长度：{content_len} 字符")


def test_validation() -> None:
    """
    测试验证与兜底功能
    """
    log_print("\n" + "=" * 60)
    log_print("  测试 3：验证与兜底")
    log_print("=" * 60)

    harness = Harness()

    class MockToolCall:
        def __init__(self, name: str, arguments: str) -> None:
            self.id: str = "call_456"
            self.function = type(
                "Function",
                (),
                {"name": name, "arguments": arguments},
            )()

    # 测试不存在的工具
    log_print("\n❌ 模拟调用不存在的工具")
    tool_call = MockToolCall(
        name="nonexistent_tool",
        arguments='{}',
    )
    result: str = harness.execute_tool(tool_call)
    log_print(f"📩 返回结果：{result}")

    # 测试非法参数
    log_print("\n❌ 模拟传递非法的计算表达式")
    tool_call = MockToolCall(
        name="calculate",
        arguments='{"expression": "import os; os.system(\'rm -rf /\')"}',
    )
    result = harness.execute_tool(tool_call)
    log_print(f"📩 返回结果：{result}")


def test_observation() -> None:
    """
    测试观测与审计功能
    """
    log_print("\n" + "=" * 60)
    log_print("  测试 4：观测与审计")
    log_print("=" * 60)

    harness = Harness()

    # 模拟 API 调用
    log_print("\n📊 模拟 LLM 调用...")
    harness.total_tokens = 150
    harness.round_count = 1
    harness.log_step(
        "调用 LLM",
        f"模型：{harness.model}，轮次：{harness.round_count}，Token 消耗：{harness.total_tokens}",
    )

    # 模拟工具调用
    log_print("\n📊 模拟工具调用...")
    harness.log_step(
        "工具路由",
        '工具名称：read_file，参数：{"path": "/tmp/test.txt"}',
    )
    # 只打印结果长度，不打印完整内容
    harness.log_step(
        "工具执行成功",
        "结果长度：11 字符（文件路径：/tmp/test.txt）",
    )


def test_full_agent_loop() -> None:
    """
    测试完整的 Agentic Loop（使用 mock 模式）
    """
    log_print("\n" + "=" * 60)
    log_print("  测试 5：完整的 Agentic Loop（mock 模式）")
    log_print("=" * 60)

    harness = Harness()

    # 由于没有真实 API，我们需要 mock call_llm 方法
    call_count: int = [0]  # 使用列表以便在嵌套函数中修改

    def mock_call_llm(user_message: str) -> dict:
        """模拟 LLM 响应"""
        call_count[0] += 1

        if call_count[0] == 1:
            # 第一次调用：返回工具调用
            log_print(f"\n  [Mock LLM] 第 {call_count[0]} 次调用，返回工具调用：read_file")
            return {
                "content": None,
                "tool_calls": [type(
                    "ToolCall",
                    (),
                    {"id": "call_mock", "function": type(
                        "Function",
                        (),
                        {"name": "read_file", "arguments": '{"path": "/tmp/test.txt"}'},
                    )()},
                )()],
            }
        else:
            # 第二次调用：返回最终回答
            log_print(f"\n  [Mock LLM] 第 {call_count[0]} 次调用，返回最终回答")
            return {
                "content": "我已成功读取文件，内容是：Hello World",
                "tool_calls": None,
            }

    # 替换 call_llm 方法
    harness.call_llm = mock_call_llm  # type: ignore

    # 运行 agent loop
    log_print("\n🔄 开始 Agentic Loop...")
    final_answer: str = harness.agent_loop("请读取 /tmp/test.txt")
    # 只打印最终回答的长度，避免打印过长内容
    log_print(f"\n✅ Loop 结束，最终回答长度：{len(final_answer)} 字符")
    log_print(f"✅ 共执行了 {call_count[0]} 轮 LLM 调用")


def main() -> None:
    """
    主测试函数
    """
    log_print("=" * 60)
    log_print("  Harness Demo - 测试脚本")
    log_print("  无需 API Key，使用 mock 模式")
    log_print("=" * 60)

    # 运行所有测试
    test_tool_routing()
    test_context_management()
    test_validation()
    test_observation()
    test_full_agent_loop()

    log_print("\n" + "=" * 60)
    log_print("  所有测试完成！")
    log_print("=" * 60)


if __name__ == "__main__":
    main()
