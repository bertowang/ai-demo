#!/usr/bin/env python3
"""
LangGraph Demo - 使用 LangGraph 构建 Agent

本 demo 展示如何使用 LangGraph 框架构建有状态的多步骤 Agent：
1. 使用 ChatOpenAI 调用 LLM（通过 Venus 平台）
2. 定义工具（Tools）供 Agent 使用
3. 使用 StateGraph 定义 Agent 的工作流程
4. 展示 LangGraph 的核心概念：状态、节点、边

作者：Berton
日期：2026-06-10

使用方法：
    python agent.py
"""

import sys
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


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
# LangGraph Agent 实现
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


class AgentState(TypedDict):
    """
    Agent 的状态定义

    LangGraph 使用 TypedDict 来定义状态，每个字段代表状态的一部分
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # messages: 对话历史（使用 add_messages 进行状态更新）


def main() -> None:
    """
    主函数：演示 LangGraph Agent 的使用
    """
    print("=" * 60)
    print("LangGraph Demo - 使用 LangGraph 构建 Agent")
    print("=" * 60)
    print(f"\n📡 URL: {BASE_URL}")
    print(f"🤖 Model: {MODEL}\n")
    print("-" * 60)

    try:
        from langchain_openai import ChatOpenAI
        from langchain.tools import tool
        from langgraph.graph import StateGraph, END, START
        from langgraph.graph.message import add_messages
        from langgraph.prebuilt import ToolNode, tools_condition
    except ImportError:
        print("❌ 未安装 langgraph 相关库")
        print("请运行：pip install langgraph langchain-openai")
        sys.exit(1)

    # ============================================================
    # 步骤 1：定义工具（使用 @tool 装饰器）
    # ============================================================
    print("\n【步骤 1】定义工具\n")

    @tool
    def get_weather_tool(city: str) -> str:
        """获取指定城市的天气信息"""
        return get_weather(city)

    @tool
    def calculate_tool(expression: str) -> str:
        """执行数学表达式计算，例如 15 * 37 或 (100 + 50) / 3"""
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

    # 绑定工具到 LLM
    llm_with_tools = llm.bind_tools(tools)

    print(f"✅ 已创建 LLM：{MODEL}")
    print(f"   API Endpoint: {BASE_URL}")
    print(f"   已绑定 {len(tools)} 个工具")

    # ============================================================
    # 步骤 3：定义 Agent 的状态
    # ============================================================
    print("\n【步骤 3】定义 Agent 的状态\n")

    print("✅ 已定义 AgentState（使用 TypedDict）")
    print("   状态包含：")
    print("   - messages: 对话历史（使用 add_messages 更新）")

    # ============================================================
    # 步骤 4：定义节点函数
    # ============================================================
    print("\n【步骤 4】定义节点函数\n")

    def call_model(state: AgentState) -> Dict[str, Any]:
        """
        调用 LLM 的节点函数

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        messages: Sequence[BaseMessage] = state["messages"]
        response: AIMessage = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    print("✅ 已定义节点函数：")
    print("   - call_model: 调用 LLM")
    print("   - tool_node: 执行工具（使用 ToolNode）")

    # ============================================================
    # 步骤 5：构建状态图（StateGraph）
    # ============================================================
    print("\n【步骤 5】构建状态图（StateGraph）\n")

    # 创建工作流图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    # 添加边（定义工作流程）
    workflow.add_edge(START, "agent")  # 从 START 到 agent
    # 条件边：根据 LLM 的输出决定下一步
    workflow.add_conditional_edges(
        "agent",
        tools_condition,  # 预构建的条件函数：如果有工具调用，去 tools；否则去 END
    )
    workflow.add_edge("tools", "agent")  # 从 tools 回到 agent
    workflow.add_edge("agent", END)  # 从 agent 到 END

    print("✅ 已构建状态图")
    print("   节点：START → agent → tools → agent → END")
    print("   条件边：根据 LLM 输出决定是否调用工具")

    # ============================================================
    # 步骤 6：编译图（创建 Agent）
    # ============================================================
    print("\n【步骤 6】编译图（创建 Agent）\n")

    app = workflow.compile()

    print("✅ 已编译图，创建 Agent")
    print("   现在可以调用 app.invoke() 执行 Agent")

    # ============================================================
    # 打印 Graph 结构
    # ============================================================
    print("\n【Graph 结构可视化】\n")

    # 方式 1：ASCII 字符图（无需额外依赖）
    print("📊 ASCII 图：")
    print(app.get_graph().draw_ascii())

    # 方式 2：Mermaid 格式（可粘贴到 https://mermaid.live 查看）
    print("\n📊 Mermaid 格式（可粘贴到 https://mermaid.live 查看）：")
    print(app.get_graph().draw_mermaid())

    # ============================================================
    # 步骤 7：执行 Agent
    # ============================================================
    print("\n" + "=" * 60)
    print("【步骤 7】执行 Agent")
    print("=" * 60)

    # 测试 1：查询天气
    print("\n📝 测试 1：查询天气\n")

    result = app.invoke({
        "messages": [HumanMessage(content="请帮我查询北京的天气")]
    })

    final_message: BaseMessage = result["messages"][-1]
    print(f"\n✅ 最终回答：{final_message.content}")

    # 打印完整的执行过程
    print_execution_process(result)

    # 测试 2：数学计算
    print("\n" + "-" * 60)
    print("\n📝 测试 2：数学计算\n")

    result = app.invoke({
        "messages": [HumanMessage(content="请计算 15 * 37 的结果")]
    })

    final_message = result["messages"][-1]
    print(f"\n✅ 最终回答：{final_message.content}")

    # 打印完整的执行过程
    print_execution_process(result)

    # 测试 3：结合工具和推理
    print("\n" + "-" * 60)
    print("\n📝 测试 3：结合工具和推理\n")

    result = app.invoke({
        "messages": [HumanMessage(content="北京和上海哪个温度更低？请先查询天气，然后告诉我")]
    })

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
    print("\nLangGraph Agent 的核心组件：")
    print("1. **State（状态）**：使用 TypedDict 定义（AgentState）")
    print("2. **Nodes（节点）**：定义每个步骤的执行逻辑（call_model, ToolNode）")
    print("3. **Edges（边）**：定义节点之间的流转（add_edge, add_conditional_edges）")
    print("4. **Graph（图）**：使用 StateGraph 构建工作流程")
    print("5. **Compile（编译）**：将图编译为可执行的 Agent")
    print("\n✅ Demo 完成！")


if __name__ == "__main__":
    main()
