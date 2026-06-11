"""
Harness Demo MCP Server

将 harness-demo 改造成 MCP Server，暴露以下 Tools：
1. agent_loop - 运行完整的 Agentic Loop
2. execute_tool - 执行单个工具
3. get_conversation_history - 获取对话历史

作者：Berton
日期：2026-06-10
"""

import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional

# ============================================================
# MCP Server 依赖检查
# ============================================================

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("❌ 错误：未安装 mcp 库，请运行：pip install mcp", file=sys.stderr)
    sys.exit(1)

# ============================================================
# 配置区域
# ============================================================

# API 配置（使用 OpenAI 兼容 API）
API_KEY: str = os.getenv(
    "OPENAI_API_KEY",
    "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",
)
BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL: str = "gpt-4o-mini"

# 安全沙箱配置：只允许访问这些目录
ALLOWED_DIRS: List[str] = [
    "/Users/berton/prj/",
    "/tmp/",
]

# ============================================================
# 工具定义（Tool Implementations）
# ============================================================


def check_path_allowed(path: str) -> bool:
    """
    检查路径是否在允许的范围内（权限与沙箱）

    Args:
        path: 要检查的路径

    Returns:
        是否允许访问
    """
    return any(path.startswith(allowed) for allowed in ALLOWED_DIRS)


def tool_read_file(path: str) -> str:
    """
    读取文件工具的实现

    Args:
        path: 文件绝对路径

    Returns:
        文件内容或错误信息
    """
    if not check_path_allowed(path):
        return f"❌ 权限错误：不允许访问 {path}（不在 ALLOWED_DIRS 内）"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content: str = f.read()
        return f"✅ 文件内容（长度：{len(content)} 字符）：\n{content[:500]}..."
    except FileNotFoundError:
        return f"❌ 文件不存在：{path}"
    except Exception as e:
        return f"❌ 读取失败：{str(e)}"


def tool_write_file(path: str, content: str) -> str:
    """
    写入文件工具的实现

    Args:
        path: 文件绝对路径
        content: 要写入的内容

    Returns:
        操作结果
    """
    if not check_path_allowed(path):
        return f"❌ 权限错误：不允许写入 {path}（不在 ALLOWED_DIRS 内）"

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ 已写入文件：{path}（{len(content)} 字符）"
    except Exception as e:
        return f"❌ 写入失败：{str(e)}"


def tool_calculate(expression: str) -> str:
    """
    计算工具的实现（安全版，只允许数学运算）

    Args:
        expression: 数学表达式

    Returns:
        计算结果或错误信息
    """
    allowed_chars: str = "0123456789+-*/.() "
    if not all(c in allowed_chars for c in expression):
        return f"❌ 非法表达式：只允许数字和运算符"

    try:
        result: float = eval(expression)  # noqa: S307
        return f"✅ 计算结果：{expression} = {result}"
    except Exception as e:
        return f"❌ 计算失败：{str(e)}"


# 工具名称 → 工具函数的映射表
TOOL_REGISTRY: Dict[str, Callable] = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "calculate": tool_calculate,
}

# ============================================================
# MCP Server 初始化
# ============================================================

# 创建 FastMCP 实例
# name: MCP Server 的名称（会显示在 Knot 等平台上）
# description: Server 的描述
mcp: FastMCP = FastMCP(
    name="harness-agent",
    description="Harness Agent MCP Server - 一个具备 Agentic Loop 能力的 AI Agent",
)

# ============================================================
# MCP Tools 定义
# ============================================================


@mcp.tool()
def agent_loop(user_input: str, model: str = MODEL, max_rounds: int = 10) -> str:
    """
    运行完整的 Agentic Loop（调用循环）

    这是一个完整的 Agent 循环：
    1. 调用 LLM
    2. 解析工具调用
    3. 执行工具
    4. 将结果加入上下文
    5. 继续循环，直到模型返回最终回答

    Args:
        user_input: 用户输入（任务描述）
        model: 使用的模型名称（默认：gpt-4o-mini）
        max_rounds: 最大调用轮数（防止无限循环，默认：10）

    Returns:
        最终回答
    """
    print(f"🔔 [MCP Tool] agent_loop 被调用，用户输入：{user_input[:50]}...", file=sys.stderr)

    # 创建 Harness 实例
    harness: Harness = Harness(model=model, max_rounds=max_rounds)

    # 运行 agent loop
    final_answer: str = harness.agent_loop(user_input)

    print(f"✅ [MCP Tool] agent_loop 完成，回答长度：{len(final_answer)} 字符", file=sys.stderr)
    return final_answer


@mcp.tool()
def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """
    执行单个工具

    直接调用指定的工具，不运行完整的 Agentic Loop。
    适用于已知需要调用哪个工具的场景。

    Args:
        tool_name: 工具名称（read_file / write_file / calculate）
        tool_args: 工具参数（字典格式）

    Returns:
        工具执行结果
    """
    print(f"🔔 [MCP Tool] execute_tool 被调用，工具：{tool_name}", file=sys.stderr)

    # 验证工具是否存在
    if tool_name not in TOOL_REGISTRY:
        return f"❌ 工具不存在：{tool_name}（可用工具：{list(TOOL_REGISTRY.keys())}）"

    # 执行工具
    tool_func: Callable = TOOL_REGISTRY[tool_name]

    try:
        result: str = tool_func(**tool_args)
        print(f"✅ [MCP Tool] execute_tool 完成，结果长度：{len(result)} 字符", file=sys.stderr)
        return result
    except Exception as e:
        return f"❌ 工具执行失败：{str(e)}"


@mcp.tool()
def get_tool_list() -> str:
    """
    获取已注册的工具列表

    Returns:
        工具列表（JSON 格式）
    """
    print(f"🔔 [MCP Tool] get_tool_list 被调用", file=sys.stderr)

    tool_list: List[Dict[str, Any]] = []

    for name, func in TOOL_REGISTRY.items():
        tool_list.append({
            "name": name,
            "description": func.__doc__ or "无描述",
            "function": func.__name__,
        })

    return json.dumps(tool_list, ensure_ascii=False, indent=2)


# ============================================================
# Harness 类（从 harness.py 移植）
# ============================================================


class Harness:
    """
    LLM Harness（运行时支撑层）

    职责：
    1. 调用循环（Agentic Loop）
    2. 工具路由与执行
    3. 上下文/记忆管理
    4. 权限与沙箱
    5. 验证与兜底
    6. 观测与审计
    """

    def __init__(self, model: str = MODEL, max_rounds: int = 10) -> None:
        """初始化 Harness"""
        self.model: str = model
        self.max_rounds: int = max_rounds
        self.conversation_history: List[Dict[str, Any]] = []
        self.total_tokens: int = 0
        self.round_count: int = 0

    def log_step(self, step_name: str, details: str = "") -> None:
        """观测与审计：记录每一步操作"""
        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"🔍 [Harness 日志] {step_name}", file=sys.stderr)
        if details:
            print(f"   {details}", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)

    def call_llm(self, user_message: str) -> Dict[str, Any]:
        """调用 LLM（封装 API 调用）"""
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        self.log_step(
            "调用 LLM",
            f"模型：{self.model}，轮次：{self.round_count + 1}/{self.max_rounds}",
        )
        print(f"📤 发送上下文长度：{len(self.conversation_history)} 条消息", file=sys.stderr)

        try:
            import openai

            client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

            response = client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "读取指定路径的文件内容",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "文件绝对路径"}
                            },
                            "required": ["path"],
                        },
                    },
                }],
                tool_choice="auto",
            )

            message = response.choices[0].message
            usage = response.usage

            if usage:
                self.total_tokens += usage.total_tokens
                print(f"📊 Token 消耗：{usage.total_tokens}（累计：{self.total_tokens}）", file=sys.stderr)

            self.conversation_history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            })

            return {
                "content": message.content,
                "tool_calls": message.tool_calls,
                "usage": usage,
            }

        except ImportError:
            return self._mock_llm_response(user_message)
        except Exception as e:
            self.log_step("LLM 调用失败", str(e))
            return {"content": f"❌ 错误：{str(e)}", "tool_calls": None}

    def _mock_llm_response(self, user_message: str) -> Dict[str, Any]:
        """模拟 LLM 响应（用于演示）"""
        self.log_step("模拟模式", "未安装 openai 库，使用模拟响应")

        if "读取" in user_message or "read" in user_message.lower():
            import re

            path_match = re.search(r"/\S+", user_message)
            path: str = path_match.group(0) if path_match else "/tmp/test.txt"

            mock_tool_call = type(
                "ToolCall",
                (),
                {
                    "id": "call_123",
                    "function": type(
                        "Function",
                        (),
                        {"name": "read_file", "arguments": json.dumps({"path": path})},
                    )(),
                },
            )()

            return {
                "content": None,
                "tool_calls": [mock_tool_call],
            }
        else:
            return {
                "content": "我已收到您的消息，但由于没有安装 openai 库，无法调用真实模型。",
                "tool_calls": None,
            }

    def agent_loop(self, user_input: str) -> str:
        """
        调用循环（Agentic Loop）：不断循环直到模型不再调用工具

        Args:
            user_input: 用户输入

        Returns:
            最终回答
        """
        print(f"\n{'🔔 ' + '=' * 58}", file=sys.stderr)
        print(f"   Harness Agentic Loop 启动", file=sys.stderr)
        print(f"{'=' * 60}", file=sys.stderr)

        self.round_count = 0

        while self.round_count < self.max_rounds:
            self.round_count += 1

            response: Dict[str, Any] = self.call_llm(user_input)

            tool_calls = response.get("tool_calls")

            if not tool_calls:
                final_answer: str = response.get("content", "")
                self.log_step(
                    "Loop 结束",
                    f"模型已给出最终回答（共 {self.round_count} 轮）",
                )
                return final_answer or "（模型未返回内容）"

            for tool_call in tool_calls:
                tool_result: str = self._execute_tool_internal(tool_call)
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

        self.log_step("Loop 超时", f"已超过最大轮数 {self.max_rounds}")
        return "⚠️ 已达到最大调用轮数，强制结束。"

    def _execute_tool_internal(self, tool_call: Any) -> str:
        """内部工具执行方法（简化版）"""
        function_name: str = tool_call.function.name
        arguments_str: str = tool_call.function.arguments

        print(f"🔍 [execute_tool] 工具：{function_name}，参数：{arguments_str}", file=sys.stderr)

        if function_name not in TOOL_REGISTRY:
            return f"❌ 工具不存在：{function_name}"

        try:
            arguments: Dict[str, Any] = json.loads(arguments_str)
        except json.JSONDecodeError:
            return f"❌ 参数解析失败：{arguments_str}"

        tool_func: Callable = TOOL_REGISTRY[function_name]

        try:
            result: str = tool_func(**arguments)
            self.log_step("工具执行成功", f"结果长度：{len(result)} 字符")
            return result
        except Exception as e:
            self.log_step("工具执行失败", str(e))
            return f"❌ 工具执行失败：{str(e)}"


# ============================================================
# 主程序入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60, file=sys.stderr)
    print("  Harness Agent MCP Server", file=sys.stderr)
    print("  " + "=" * 58, file=sys.stderr)
    print(f"  名称：{mcp.name}", file=sys.stderr)
    print(f"  描述：{mcp.description}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # 启动 MCP Server（stdio 模式）
    mcp.run()
