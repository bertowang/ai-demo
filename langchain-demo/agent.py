#!/usr/bin/env python3
"""
LangChain Demo - 使用 LangChain 构建 Agent

本 demo 展示如何使用 LangChain 1.x 框架构建 Agent：
1. 使用 ChatOpenAI 调用 LLM（通过 Venus 平台）
2. 定义工具（Tools）供 Agent 使用
3. 使用 create_agent 创建 Agent（LangChain 1.x 新 API）
4. 展示完整的 Agent 工作流程

注意：本 demo 使用 LangChain 1.x 版本，其中 create_agent 是直接
      返回 LangGraph CompiledStateGraph 的新 API。

作者：Berton
日期：2026-06-10

使用方法：
    python agent.py
"""

import sys
from typing import Any, Dict, List, Optional

# ============================================================
# 配置区域
# ============================================================

# Venus 平台 API 配置（腾讯内部 LLM 代理服务）
# 参考文档：https://iwiki.woa.com/p/4009937875
API_KEY: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
BASE_URL: str = "http://v2.open.venus.oa.com/llmproxy"
MODEL: str = "gpt-4o-mini"  # Venus 平台支持的模型

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
        "广州": "阴天，29°C",
    }
    return weather_data.get(city, f"未知城市：{city}，无法查询天气")


def calculate(expression: str) -> str:
    """
    执行数学表达式计算

    Args:
        expression: 数学表达式，例如 "15 * 37"

    Returns:
        计算结果
    """
    try:
        # 安全评估数学表达式（仅允许基本运算符）
        allowed_chars: str = "0123456789+-*/.() "
        if all(c in allowed_chars for c in expression):
            result: float = eval(expression)  # noqa: S307
            return f"✅ 计算结果：{expression} = {result}"
        else:
            return "❌ 表达式包含不允许的字符"
    except Exception as e:
        return f"❌ 计算失败：{str(e)}"


# ============================================================
# LangChain Agent 实现（使用 LangChain 1.x API）
# ============================================================

def print_execution_process(result: Dict[str, Any]) -> None:
    """
    打印 Agent 执行的完整过程
    
    Args:
        result: Agent 执行后的结果，包含 messages 列表
    """
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    
    print("\n" + "=" * 60)
    print("📊 执行过程（共 {} 条消息）".format(len(result["messages"])))
    print("=" * 60)
    
    for i, msg in enumerate(result["messages"]):
        print(f"\n[消息 {i+1}]")
        
        if isinstance(msg, HumanMessage):
            print("  📝 类型: HumanMessage (用户输入)")
            print(f"  💬 内容: {msg.content}")
            
        elif isinstance(msg, AIMessage):
            # 检查是否有工具调用
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print("  🤖 类型: AIMessage (AI 调用工具)")
                print(f"  🔧 工具调用: ")
                for tc in msg.tool_calls:
                    print(f"     - 工具名: {tc.get('name', 'N/A')}")
                    print(f"     - 参数: {tc.get('args', 'N/A')}")
            else:
                print("  🤖 类型: AIMessage (AI 回复)")
                print(f"  💬 内容: {msg.content}")
                
        elif isinstance(msg, ToolMessage):
            print("  🔧 类型: ToolMessage (工具返回)")
            print(f"  📊 结果: {msg.content}")
            # 打印工具调用 ID（如果有）
            if hasattr(msg, 'tool_call_id'):
                print(f"  🔗 关联调用 ID: {msg.tool_call_id}")
        
        else:
            # 处理其他未知类型的消息
            print(f"  ❓ 类型: {type(msg).__name__}")
            print(f"  📄 内容: {msg}")
    
    print("\n" + "=" * 60)
    print("✅ 执行过程打印完成")
    print("=" * 60)


def main() -> None:
    """
    主函数：演示 LangChain 1.x Agent 的使用
    """
    print("=" * 60)
    print("LangChain Demo - 使用 LangChain 1.x 构建 Agent")
    print("=" * 60)
    print(f"\n📡 URL: {BASE_URL}")
    print(f"🤖 Model: {MODEL}\n")
    print("-" * 60)

    try:
        from langchain_openai import ChatOpenAI
        from langchain.agents import create_agent
        from langchain.tools import tool
    except ImportError:
        print("❌ 未安装 langchain 相关库")
        print("请运行：pip install langchain langchain-openai")
        sys.exit(1)

    # ============================================================
    # 步骤 1：定义工具（使用 @tool 装饰器）
    # ============================================================
    print("\n【步骤 1】定义工具\n")

    @tool
    def get_weather_tool(city: str) -> str:
        """获取指定城市的天气信息。"""
        return get_weather(city)

    @tool
    def calculate_tool(expression: str) -> str:
        """执行数学表达式计算，例如 15 * 37 或 (100 + 50) / 3。"""
        return calculate(expression)

    # 工具列表
    tools: List = [get_weather_tool, calculate_tool]

    print(f"✅ 已定义 {len(tools)} 个工具：")
    for t in tools:
        print(f"   - {t.name}: {t.description}")

    # ============================================================
    # 步骤 2：创建 LLM（大语言模型）
    # ============================================================
    print("\n【步骤 2】创建 LLM（大语言模型）\n")

    llm = ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=0.7,
    )

    print(f"✅ 已创建 LLM：{MODEL}")
    print(f"   API Endpoint: {BASE_URL}")

    # ============================================================
    # 步骤 3：使用 create_agent 创建 Agent（LangChain 1.x 新 API）
    # ============================================================
    print("\n【步骤 3】使用 create_agent 创建 Agent（LangChain 1.x 新 API）\n")

    # LangChain 1.x 的 create_agent 直接返回一个编译好的 LangGraph CompiledStateGraph
    # 参数说明：
    # - model: 模型（可以是字符串如 "openai:gpt-4o-mini" 或 ChatModel 实例）
    # - tools: 工具列表
    # - system_prompt: 系统提示词
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个有帮助的助手，可以使用工具来回答用户的问题。",
    )

    print("✅ 已创建 Agent（使用 create_agent）")
    print("   create_agent 直接返回一个编译好的 LangGraph CompiledStateGraph")
    print("   Agent 可以：")
    print("   1. 理解用户输入")
    print("   2. 决定是否需要调用工具")
    print("   3. 解析工具调用参数")
    print("   4. 根据工具结果生成最终回答")

    # ============================================================
    # 步骤 4：执行 Agent
    # ============================================================
    print("\n" + "=" * 60)
    print("【步骤 4】执行 Agent")
    print("=" * 60)

    # 测试 1：查询天气
    print("\n📝 测试 1：查询天气\n")
    result = agent.invoke({"messages": [("human", "请帮我查询北京的天气")]})
    
    # 获取最终回答（最后一个 AI 消息）
    final_message = result["messages"][-1]
    print(f"\n✅ 最终回答：{final_message.content}")

    # 打印完整的执行过程
    print_execution_process(result)

    # 测试 2：数学计算
    print("\n" + "-" * 60)
    print("\n📝 测试 2：数学计算\n")
    result = agent.invoke({"messages": [("human", "请计算 15 * 37 的结果")]})
    final_message = result["messages"][-1]
    print(f"\n✅ 最终回答：{final_message.content}")
    
    # 打印完整的执行过程
    print_execution_process(result)

    # 测试 3：结合工具和推理
    print("\n" + "-" * 60)
    print("\n📝 测试 3：结合工具和推理\n")
    result = agent.invoke({"messages": [("human", "北京和上海哪个温度更低？请先查询天气，然后告诉我")]})
    final_message = result["messages"][-1]
    print(f"\n✅ 最终回答：{final_message.content}")
    
    # 打印完整的执行过程
    print_execution_process(result)

    # ============================================================
    # 总结
    # ============================================================
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("\nLangChain 1.x Agent 的核心组件：")
    print("1. **Tools（工具）**：使用 @tool 装饰器定义")
    print("2. **LLM（大语言模型）**：使用 ChatOpenAI")
    print("3. **create_agent**：创建 Agent（新 API，返回 CompiledStateGraph）")
    print("4. **agent.invoke()**：执行 Agent")
    print("\n✅ Demo 完成！")


if __name__ == "__main__":
    main()