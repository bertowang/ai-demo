"""
Harness Demo - LLM 运行时支撑层演示

本文件实现了一个最简化的 Harness，展示 Harness 的六大核心职责：
1. 调用循环（Agentic Loop）
3. 工具路由与执行
4. 上下文/记忆管理
5. 权限与沙箱
6. 验证与兜底
7. 观测与审计

作者：Berton
日期：2026-06-10
"""

import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional

# ============================================================
# 配置区域
# ============================================================

# API 配置（使用 OpenAI 兼容 API）
API_KEY: str = os.getenv("OPENAI_API_KEY", "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")
BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL: str = "gpt-4o-mini"  # 或其他支持 tool calling 的模型

# 安全沙箱配置：只允许访问这些目录
ALLOWED_DIRS: List[str] = [
    "/Users/berton/prj/",
    "/tmp/",
]

# ============================================================
# 工具定义（Tool Schema）
# ============================================================

# 工具清单：告诉模型有哪些工具可用
# 这是 Function Calling 的标准格式
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定路径的文件内容。只能读取 ALLOWED_DIRS 内的文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件绝对路径，例如 /Users/berton/prj/test.txt",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "向指定路径写入内容。只能写入 ALLOWED_DIRS 内的文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件绝对路径",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学表达式计算，例如 15 * 37 或 (100 + 50) / 3",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，例如 15 * 37",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]


# ============================================================
# 工具实现（Tool Implementations）
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
    # 权限检查（沙箱）
    if not check_path_allowed(path):
        return f"❌ 权限错误：不允许访问 {path}（不在 ALLOWED_DIRS 内）"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content: str = f.read()
        return f"✅ 文件内容：\n{content}"
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
    # 权限检查（沙箱）
    if not check_path_allowed(path):
        return f"❌ 权限错误：不允许写入 {path}（不在 ALLOWED_DIRS 内）"

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ 已写入文件：{path}"
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
    # 安全验证：只允许数字、运算符和括号
    allowed_chars: str = "0123456789+-*/.() "
    if not all(c in allowed_chars for c in expression):
        return f"❌ 非法表达式：只允许数字和运算符"

    try:
        result: float = eval(expression)  # noqa: S307
        return f"✅ 计算结果：{expression} = {result}"
    except Exception as e:
        return f"❌ 计算失败：{str(e)}"


# 工具名称 → 工具函数的映射表（工具路由）
# 注意：TOOL_REGISTRY 只在第 187-191 行赋值一次，后续不会被修改
# 所有可用的工具都必须在这里注册，否则 execute_tool 会返回"工具不存在"错误
print("\n" + "=" * 60)
print("🔧 [初始化] TOOL_REGISTRY 注册表")
print(f"   已注册工具数量：{len(['read_file', 'write_file', 'calculate'])} 个")
print(f"   已注册工具列表：{', '.join(['read_file', 'write_file', 'calculate'])}")
print("=" * 60)

TOOL_REGISTRY: Dict[str, Callable] = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "calculate": tool_calculate,
}

print(f"✅ TOOL_REGISTRY 初始化完成，类型：{type(TOOL_REGISTRY).__name__}")
print(f"✅ 注册表内容：{ {k: v.__name__ for k, v in TOOL_REGISTRY.items()} }\n")


# ============================================================
# Harness 核心组件
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
        """
        初始化 Harness
        
        Args:
            model: 使用的模型名称
            max_rounds: 最大调用轮数（防止无限循环）
        """
        self.model: str = model
        self.max_rounds: int = max_rounds
        self.conversation_history: List[Dict[str, Any]] = []
        self.total_tokens: int = 0
        self.round_count: int = 0

    def log_step(self, step_name: str, details: str = "") -> None:
        """
        观测与审计：记录每一步操作
        
        Args:
            step_name: 步骤名称
            details: 详细信息
        """
        print(f"\n{'=' * 60}")
        print(f"🔍 [Harness 日志] {step_name}")
        if details:
            print(f"   {details}")
        print(f"{'=' * 60}")

    def call_llm(self, user_message: str) -> Dict[str, Any]:
        """
        调用 LLM（封装 API 调用）
        
        Args:
            user_message: 用户消息
            
        Returns:
            LLM 的响应
        """
        # 添加用户消息到上下文（上下文管理）
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        self.log_step(
            "调用 LLM",
            f"模型：{self.model}，轮次：{self.round_count + 1}/{self.max_rounds}",
        )
        print(f"📤 发送上下文长度：{len(self.conversation_history)} 条消息")

        # 实际调用 API（这里使用 OpenAI 兼容格式）
        try:
            import openai

            client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

            response = client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )

            message = response.choices[0].message
            usage = response.usage

            # 观测：记录 token 消耗
            if usage:
                self.total_tokens += usage.total_tokens
                print(f"📊 Token 消耗：{usage.total_tokens}（累计：{self.total_tokens}）")

            # 将助手回复添加到上下文（上下文管理）
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
            # 如果没有安装 openai 库，使用模拟模式
            return self._mock_llm_response(user_message)
        except Exception as e:
            self.log_step("LLM 调用失败", str(e))
            return {"content": f"❌ 错误：{str(e)}", "tool_calls": None}

    def _mock_llm_response(self, user_message: str) -> Dict[str, Any]:
        """
        模拟 LLM 响应（用于演示，无需真实 API Key）
        
        Args:
            user_message: 用户消息
            
        Returns:
            模拟的 LLM 响应
        """
        self.log_step("模拟模式", "未安装 openai 库，使用模拟响应")

        # 简单的模拟逻辑：根据用户输入判断应该调用哪个工具
        if "读取" in user_message or "read" in user_message.lower():
            # 模拟调用 read_file 工具
            import re
            path_match = re.search(r"/\S+", user_message)
            path: str = path_match.group(0) if path_match else "/Users/berton/prj/mcp-demo-all/harness-demo/harness.py"

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
        elif "计算" in user_message or "calculate" in user_message.lower():
            # 模拟调用 calculate 工具
            mock_tool_call = type(
                "ToolCall",
                (),
                {
                    "id": "call_456",
                    "function": type(
                        "Function",
                        (),
                        {"name": "calculate", "arguments": json.dumps({"expression": "15 * 37"})},
                    )(),
                },
            )()

            return {
                "content": None,
                "tool_calls": [mock_tool_call],
            }
        else:
            return {
                "content": "我已收到您的消息，但由于没有安装 openai 库，无法调用真实模型。请安装 openai 库后重试。",
                "tool_calls": None,
            }

    def execute_tool(self, tool_call: Any) -> str:
        """
        工具路由与执行：根据模型输出，调用对应的工具函数
        
        Args:
            tool_call: LLM 返回的工具调用对象
            
        Returns:
            工具执行结果
        """
        function_name: str = tool_call.function.name
        arguments_str: str = tool_call.function.arguments
        
        # 【日志 1】打印 function_name 和 arguments_str
        print(f"\n{'=' * 60}")
        print(f"🔍 [execute_tool] 收到工具调用请求")
        print(f"   function_name: {function_name}")
        print(f"   arguments_str: {arguments_str}")
        print(f"   TOOL_REGISTRY 类型: {type(TOOL_REGISTRY).__name__}")
        print(f"   TOOL_REGISTRY 已注册工具: {list(TOOL_REGISTRY.keys())}")
        print(f"{'=' * 60}")

        self.log_step(
            "工具路由",
            f"工具名称：{function_name}，参数：{arguments_str}",
        )

        # 验证：检查工具是否存在（验证与兜底）
        if function_name not in TOOL_REGISTRY:
            print(f"❌ 工具路由失败：{function_name} 不在 TOOL_REGISTRY 中")
            print(f"   可用工具：{list(TOOL_REGISTRY.keys())}")
            return f"❌ 工具不存在：{function_name}"

        # 解析参数
        try:
            arguments: Dict[str, Any] = json.loads(arguments_str)
            print(f"✅ 参数解析成功：{arguments}")
        except json.JSONDecodeError as e:
            print(f"❌ 参数解析失败：{arguments_str}")
            return f"❌ 参数解析失败：{arguments_str}"

        # 【日志 2】导航到具体的 tool_func
        print(f"\n{'=' * 60}")
        print(f"🧭 [工具路由] 开始导航...")
        print(f"   第 1 步：从 TOOL_REGISTRY 中查找 '{function_name}'")
        print(f"   第 2 步：TOOL_REGISTRY['{function_name}'] = {TOOL_REGISTRY[function_name].__name__}")
        print(f"   第 3 步：获取函数对象 {TOOL_REGISTRY[function_name]}")
        
        # 路由到对应的工具函数并执行
        tool_func: Callable = TOOL_REGISTRY[function_name]
        
        print(f"   第 4 步：准备调用 {tool_func.__name__}(**{arguments})")
        print(f"{'=' * 60}\n")
        
        try:
            result: str = tool_func(**arguments)
            # 只打印结果长度，避免打印过长的完整结果
            self.log_step("工具执行成功", f"结果长度：{len(result)} 字符")
            return result
        except Exception as e:
            self.log_step("工具执行失败", str(e))
            return f"❌ 工具执行失败：{str(e)}"

    def agent_loop(self, user_input: str) -> str:
        """
        调用循环（Agentic Loop）：不断循环直到模型不再调用工具
        
        Args:
            user_input: 用户输入
            
        Returns:
            最终回答
        """
        print(f"\n{'🔔 ' + '=' * 58}")
        print(f"   Harness Agentic Loop 启动")
        print(f"{'=' * 60}")

        self.round_count = 0

        # 主循环：调用模型 → 解析工具调用 → 执行工具 → 继续循环
        while self.round_count < self.max_rounds:
            self.round_count += 1

            # 1. 调用 LLM
            response: Dict[str, Any] = self.call_llm(user_input)

            # 2. 检查是否需要调用工具
            tool_calls = response.get("tool_calls")

            if not tool_calls:
                # 不需要调用工具，直接返回最终回答
                final_answer: str = response.get("content", "")
                self.log_step(
                    "Loop 结束",
                    f"模型已给出最终回答（共 {self.round_count} 轮）",
                )
                return final_answer or "（模型未返回内容）"

            # 3. 需要调用工具：遍历所有工具调用
            for tool_call in tool_calls:
                # 执行工具
                tool_result: str = self.execute_tool(tool_call)

                # 4. 将工具结果添加到上下文（上下文管理）
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            # 5. 继续循环（让模型根据工具结果生成后续回答或调用更多工具）

        # 超过最大轮数
        self.log_step("Loop 超时", f"已超过最大轮数 {self.max_rounds}")
        return "⚠️ 已达到最大调用轮数，强制结束。"


# ============================================================
# 主程序入口
# ============================================================

def main() -> None:
    """
    主程序：演示 Harness 的使用
    """
    print("=" * 60)
    print("  Harness Demo - LLM 运行时支撑层演示")
    print("=" * 60)

    # 创建 Harness 实例
    harness: Harness = Harness(model=MODEL, max_rounds=10)

    # 演示对话 1：让模型读取文件
    print("\n\n【演示 1】让模型读取文件")
    user_input_1: str = "请帮我读取 /Users/berton/prj/mcp-demo-all/harness-demo/harness.py 这个文件的前 50 行"
    final_answer_1: str = harness.agent_loop(user_input_1)
    print(f"\n✅ 最终回答：\n{final_answer_1}")

    # 演示对话 2：让模型计算
    print("\n\n【演示 2】让模型计算")
    user_input_2: str = "请计算 15 * 37 的结果"
    final_answer_2: str = harness.agent_loop(user_input_2)
    print(f"\n✅ 最终回答：\n{final_answer_2}")

    print("\n\n")
    print("=" * 60)
    print(f"  演示完成！累计消耗 Token：{harness.total_tokens}")
    print("=" * 60)


if __name__ == "__main__":
    main()
