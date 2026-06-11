#!/usr/bin/env python3
"""
Simple Agent Demo - 最简单的 Agent 实现

本 demo 展示一个最基础的 Agent，包含：
1. 调用 LLM（使用 OpenAI API 或模拟模式）
2. 工具调用能力（Function Calling）
3. Agentic Loop（调用循环）
4. 上下文管理

作者：Berton
日期：2026-06-10

使用方法：
1. 如果有 OpenAI API key，直接运行：python agent.py
2. 如果没有 API key，使用模拟模式：python agent.py --mock
"""

import argparse
import json
import sys
from typing import Any, Callable, Dict, List, Optional

# 尝试导入 openai，如果失败则使用模拟模式
try:
    import openai

    OPENAI_AVAILABLE: bool = True
except ImportError:
    OPENAI_AVAILABLE: bool = False
    print("⚠️  未安装 openai 库，将使用模拟模式")


# ============================================================
# 配置区域
# ============================================================

# Venus 平台 API 配置（腾讯内部 LLM 代理服务）
# 参考文档：https://iwiki.woa.com/p/4009937875
API_KEY: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
BASE_URL: str = "http://v2.open.venus.oa.com/llmproxy"
MODEL: str = "gpt-4o-mini"  # Venus 平台支持的模型

# 注意：Venus 平台的 URL 不需要 /v1 后缀
# OpenAI 客户端会自动添加 /chat/completions 路径

# ============================================================
# 工具定义（Tools）
# ============================================================


def get_weather(city: str) -> str:
    """
    获取指定城市的天气（模拟工具）

    Args:
        city: 城市名称

    Returns:
        天气信息
    """
    # 模拟天气数据
    weather_data: Dict[str, str] = {
        "北京": "晴天，25°C",
        "上海": "多云，28°C",
        "深圳": "雨天，30°C",
    }
    return weather_data.get(city, f"抱歉，暂时无法查询 {city} 的天气")


def calculate(expression: str) -> str:
    """
    执行数学计算（模拟工具）

    Args:
        expression: 数学表达式

    Returns:
        计算结果
    """
    try:
        # 安全计算（只允许数字和运算符）
        allowed_chars: str = "0123456789+-*/.() "
        if not all(c in allowed_chars for c in expression):
            return "❌ 非法表达式"

        result: float = eval(expression)  # noqa: S307
        return f"✅ 计算结果：{expression} = {result}"
    except Exception as e:
        return f"❌ 计算失败：{str(e)}"


# 工具名称 → 工具函数的映射表
TOOL_REGISTRY: Dict[str, Callable] = {
    "get_weather": get_weather,
    "calculate": calculate,
}


# 工具 Schema（告诉 LLM 有哪些工具可用）
TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海、深圳",
                    }
                },
                "required": ["city"],
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
# Agent 类
# ============================================================


class SimpleAgent:
    """
    最简单的 Agent 实现

    核心能力：
    1. 调用 LLM（决策）
    2. 执行工具（行动）
    3. Agentic Loop（自主循环）
    4. 上下文管理（记忆）
    """

    def __init__(self, model: str = MODEL, max_rounds: int = 10, mock_mode: bool = False) -> None:
        """
        初始化 Agent

        Args:
            model: 使用的模型名称
            max_rounds: 最大调用轮数（防止无限循环）
            mock_mode: 是否使用模拟模式（不需要真实 API）
        """
        self.model: str = model
        self.max_rounds: int = max_rounds
        self.mock_mode: bool = mock_mode
        self.conversation_history: List[Dict[str, Any]] = []
        
        # 只有在非模拟模式且 openai 可用时才创建 client
        if not mock_mode and OPENAI_AVAILABLE:
            self.client: openai.OpenAI = openai.OpenAI(
                api_key=API_KEY,
                base_url=BASE_URL,
            )
        else:
            self.client = None
            if not mock_mode:
                print("⚠️  openai 库不可用，自动切换到模拟模式")
                self.mock_mode = True

    def call_llm(self, user_message: str) -> Dict[str, Any]:
        """
        调用 LLM（决策中枢）

        Args:
            user_message: 用户消息

        Returns:
            LLM 响应（包含内容或工具调用）
        """
        # 将用户消息添加到上下文
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        print(f"\n🔄 [Agent] 调用 LLM（轮次 {len(self.conversation_history)}）...")
        print(f"   模型：{self.model}")
        
        # 如果是模拟模式，直接调用模拟函数
        if self.mock_mode:
            print("   📝 使用模拟模式")
            response: Dict[str, Any] = self._mock_llm_response(user_message)
            
            # 将助手回复添加到上下文（模拟模式也需要）
            self.conversation_history.append({
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": response.get("tool_calls"),
            })
            
            return response

        # 否则调用真实 API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
            )

            message = response.choices[0].message
            print(f"   📝 LLM 响应：{response} --- {message}")

            # 将助手回复添加到上下文
            self.conversation_history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            })

            return {
                "content": message.content,
                "tool_calls": message.tool_calls,
            }
        except Exception as e:
            print(f"   ⚠️  API 调用失败，切换到模拟模式：{str(e)}")
            self.mock_mode = True
            response = self._mock_llm_response(user_message)
            
            # 将助手回复添加到上下文（模拟模式也需要）
            self.conversation_history.append({
                "role": "assistant",
                "content": response.get("content"),
                "tool_calls": response.get("tool_calls"),
            })
            
            return response

    def _mock_llm_response(self, user_message: str) -> Dict[str, Any]:
        """
        模拟 LLM 响应（用于演示和测试）

        简化版本：根据当前用户消息返回预设响应
        """
        print(f"   📝 模拟模式")
        
        # 检查上一次是否调用了工具（通过检查最后一条助手消息）
        last_assistant_message: Optional[Dict[str, Any]] = None
        for msg in reversed(self.conversation_history):
            if msg.get("role") == "assistant":
                last_assistant_message = msg
                break
        
        # 如果上一次调用了工具，这次返回最终答案
        if last_assistant_message and last_assistant_message.get("tool_calls"):
            # 获取工具执行结果
            last_tool_result: str = ""
            for msg in reversed(self.conversation_history):
                if msg.get("role") == "tool":
                    last_tool_result = msg.get("content", "")
                    break
            
            return {
                "content": f"根据工具执行结果：{last_tool_result}。这就是您要的答案！",
                "tool_calls": None,
            }

        # 否则，根据用户消息决定是调用工具还是直接回答
        if "天气" in user_message:
            # 提取城市名称
            city: str = "北京"
            if "上海" in user_message:
                city = "上海"
            elif "深圳" in user_message:
                city = "深圳"
            elif "北京" in user_message:
                city = "北京"

            # 模拟工具调用
            mock_tool_call = type(
                "ToolCall",
                (),
                {
                    "id": "call_123",
                    "function": type(
                        "Function",
                        (),
                        {"name": "get_weather", "arguments": json.dumps({"city": city})},
                    )(),
                },
            )()

            print(f"   📝 模拟调用工具：get_weather(city='{city}')")
            
            return {
                "content": None,
                "tool_calls": [mock_tool_call],
            }
        elif "计算" in user_message or "*" in user_message or "+" in user_message:
            # 提取数学表达式
            expression: str = "15 * 37"
            if "15 * 37" in user_message:
                expression = "15 * 37"

            # 模拟工具调用
            mock_tool_call = type(
                "ToolCall",
                (),
                {
                    "id": "call_456",
                    "function": type(
                        "Function",
                        (),
                        {"name": "calculate", "arguments": json.dumps({"expression": expression})},
                    )(),
                },
            )()

            print(f"   📝 模拟调用工具：calculate(expression='{expression}')")
            
            return {
                "content": None,
                "tool_calls": [mock_tool_call],
            }
        else:
            # 直接返回回答
            return {
                "content": f"我已收到您的消息：{user_message}。这是模拟回答。",
                "tool_calls": None,
            }

    def execute_tool(self, tool_call: Any) -> str:
        """
        执行工具（行动）

        Args:
            tool_call: 工具调用对象

        Returns:
            工具执行结果
        """
        function_name: str = tool_call.function.name
        arguments_str: str = tool_call.function.arguments

        print(f"\n🔧 [Agent] 执行工具：{function_name}")
        print(f"   参数：{arguments_str}")

        # 验证工具是否存在
        if function_name not in TOOL_REGISTRY:
            return f"❌ 工具不存在：{function_name}"

        # 解析参数
        try:
            arguments: Dict[str, Any] = json.loads(arguments_str)
        except json.JSONDecodeError:
            return f"❌ 参数解析失败：{arguments_str}"

        # 执行工具
        tool_func: Callable = TOOL_REGISTRY[function_name]
        result: str = tool_func(**arguments)

        print(f"   结果：{result[:100]}...")  # 只打印前 100 字符

        return result

    def run(self, user_input: str) -> str:
        """
        Agentic Loop（自主循环）

        流程：
        1. 调用 LLM
        2. 检查是否需要调用工具
        3. 如果需要，执行工具并将结果加入上下文
        4. 继续循环，直到模型返回最终回答

        Args:
            user_input: 用户输入

        Returns:
            最终回答
        """
        print(f"\n{'=' * 60}")
        print(f"  Simple Agent 启动")
        print(f"  用户输入：{user_input}")
        print(f"{'=' * 60}")

        round_count: int = 0

        while round_count < self.max_rounds:
            round_count += 1

            # 1. 调用 LLM
            response: Dict[str, Any] = self.call_llm(user_input)

            # 2. 检查是否需要调用工具
            tool_calls = response.get("tool_calls")
            print(f"   工具调用：{tool_calls}")
            if not tool_calls:
                # 不需要调用工具，直接返回最终回答
                final_answer: str = response.get("content", "")
                print(f"\n✅ [Agent] 完成（共 {round_count} 轮）")
                print(f"   最终回答：{final_answer}")
                return final_answer or "（模型未返回内容）"

            # 3. 需要调用工具：遍历所有工具调用
            print(f"   需要调用工具：{tool_calls}")
            for tool_call in tool_calls:
                # 执行工具
                tool_result: str = self.execute_tool(tool_call)

                # 4. 将工具结果添加到上下文
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

                print(f"   工具结果：{tool_result}")
            # 5. 继续循环（让模型根据工具结果生成后续回答）

        # 超过最大轮数
        print(f"\n⚠️  [Agent] 超过最大轮数 {self.max_rounds}")
        return "⚠️ 已达到最大调用轮数，强制结束。"


# ============================================================
# 主程序
# ============================================================


def main() -> None:
    """
    主程序：演示 Simple Agent 的使用
    """
    # 解析命令行参数
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Simple Agent Demo - 最简单的 Agent 实现"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用模拟模式（不需要真实 OpenAI API）",
    )
    args: argparse.Namespace = parser.parse_args()
    
    print("=" * 60)
    print("  Simple Agent Demo")
    print("=" * 60)
    
    if args.mock:
        print("\n📝 运行模式：模拟模式（不需要 OpenAI API）")
    else:
        print("\n🌐 运行模式：真实 API 模式（需要 OpenAI API）")

    # 创建 Agent 实例
    agent: SimpleAgent = SimpleAgent(mock_mode=args.mock)

    # 演示 1：让 Agent 查询天气
    print("\n\n【演示 1】查询天气")
    user_input_1: str = "请帮我查询北京的天气"
    agent.run(user_input_1)

    # 演示 2：让 Agent 计算
    print("\n\n【演示 2】数学计算")
    user_input_2: str = "请计算 15 * 37 的结果"
    agent.run(user_input_2)

    # 演示 3：让 Agent 结合工具和推理
    print("\n\n【演示 3】结合工具和推理")
    user_input_3: str = "北京和上海哪个温度更低？请先查询天气，然后告诉我"
    agent.run(user_input_3)

    print("\n\n")
    print("=" * 60)
    print("  演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
