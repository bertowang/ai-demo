#!/usr/bin/env python3
"""
LangGraph Multi-Agent Demo (Simplified Version)

Simplified architecture:
- No complex supervisor logic
- Sequential execution: weather -> calculator -> finish
- Simple conditional routing based on state

Author: Berton
Date: 2026-06-11

Usage:
    python agent.py
"""

import sys
from typing import Annotated, Any, Dict, Sequence, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool

# ============================================================
# Configuration
# ============================================================

API_KEY: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
BASE_URL: str = "http://v2.open.venus.oa.com/llmproxy"
MODEL: str = "gpt-4o-mini"


# ============================================================
# Tool Functions
# ============================================================


def get_weather(city: str) -> str:
    """Get weather for a city"""
    weather_data: Dict[str, str] = {
        "Beijing": "Sunny, 25C",
        "Shanghai": "Cloudy, 28C",
        "Shenzhen": "Rainy, 30C",
        "Guangzhou": "Overcast, 29C",
    }
    return weather_data.get(city, f"Unknown city: {city}")


def calculate(expression: str) -> str:
    """Calculate math expression"""
    try:
        allowed_chars: str = "0123456789+-*/.() "
        if all(c in allowed_chars for c in expression):
            result: float = eval(expression)  # noqa: S307
            return f"Result: {expression} = {result}"
        else:
            return "Invalid expression"
    except Exception as e:
        return f"Calculation failed: {str(e)}"


# ============================================================
# State Definition
# ============================================================


class AgentState(TypedDict):
    """Shared state for all agents"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    weather_done: bool  # Whether weather agent has finished
    calc_done: bool  # Whether calculator agent has finished


# ============================================================
# LLM Factory
# ============================================================


def create_llm(temperature: float = 0.7) -> ChatOpenAI:
    """Create LLM instance"""
    return ChatOpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        temperature=temperature,
    )


# ============================================================
# Agent Nodes (Simple - just call LLM)
# ============================================================


def create_weather_node():
    """Create weather agent node"""
    llm = create_llm(0.3)
    
    @tool
    def weather_tool(city: str) -> str:
        """Get weather for a city."""
        return get_weather(city)
    
    tools = [weather_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    def node(state: AgentState) -> Dict[str, Any]:
        """Weather agent node"""
        print("  [Weather Agent] Processing...")
        messages: Sequence[BaseMessage] = state["messages"]
        # 如果已有工具结果，添加系统提示要求直接总结，避免重复调用工具
        has_tool_result = any(isinstance(m, ToolMessage) for m in messages)
        if has_tool_result:
            from langchain_core.messages import SystemMessage
            invoke_messages = list(messages) + [SystemMessage(content="You already have the tool results. Please summarize and answer directly without calling any more tools.")]
        else:
            invoke_messages = list(messages)
        
        print(f"  [Debug] invoke_messages: {invoke_messages}")
        print(f"  [Debug] llm_with_tools: {llm_with_tools}")
        response: AIMessage = llm_with_tools.invoke(invoke_messages)
        return {"messages": [response], "weather_done": False, "calc_done": state.get("calc_done", False)}
    
    def after_tools(state: AgentState) -> Dict[str, Any]:
        """After weather tools - mark weather as done"""
        print("  [Weather Agent] Task completed")
        return {"weather_done": True}
    
    return {
        "node": node,
        "tools": ToolNode(tools),
        "after_tools": after_tools,
    }


def create_calculator_node():
    """Create calculator agent node"""
    llm = create_llm(0.1)
    
    @tool
    def calc_tool(expression: str) -> str:
        """Calculate math expression."""
        return calculate(expression)
    
    tools = [calc_tool]
    llm_with_tools = llm.bind_tools(tools)
    
    def node(state: AgentState) -> Dict[str, Any]:
        """Calculator agent node"""
        print("  [Calculator Agent] Processing...")
        messages: Sequence[BaseMessage] = state["messages"]
        # 如果已有计算工具结果，添加系统提示要求直接总结，避免重复调用工具
        has_calc_result = any(
            isinstance(m, ToolMessage) and "Result:" in m.content
            for m in messages
        )
        if has_calc_result:
            from langchain_core.messages import SystemMessage
            invoke_messages = list(messages) + [SystemMessage(content="You already have the calculation result. Please summarize and answer directly without calling any more tools.")]
        else:
            invoke_messages = list(messages)
        response: AIMessage = llm_with_tools.invoke(invoke_messages)
        return {"messages": [response], "calc_done": False, "weather_done": state.get("weather_done", False)}
    
    def after_tools(state: AgentState) -> Dict[str, Any]:
        """After calculator tools - mark calc as done"""
        print("  [Calculator Agent] Task completed")
        return {"calc_done": True}
    
    return {
        "node": node,
        "tools": ToolNode(tools),
        "after_tools": after_tools,
    }


# ============================================================
# Routing Functions
# ============================================================


def route_weather(state: AgentState) -> str:
    """Route weather agent output"""
    messages = state["messages"]
    last_msg = messages[-1]
    
    # If tool calls, go to tools
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        print("  [Router] Weather: Tool call detected")
        return "weather_tools"
    
    # Otherwise, mark done and finish
    print("  [Router] Weather: No tool call, finishing")
    return "weather_done"


def route_calculator(state: AgentState) -> str:
    """Route calculator agent output"""
    messages = state["messages"]
    last_msg = messages[-1]
    
    # If tool calls, go to tools
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        print("  [Router] Calculator: Tool call detected")
        return "calculator_tools"
    
    # Otherwise, mark done and finish
    print("  [Router] Calculator: No tool call, finishing")
    return "calculator_done"


def should_continue(state: AgentState) -> str:
    """Decide whether to call calculator or finish"""
    # If weather done and user asked for calculation, call calculator
    user_request = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            user_request = msg.content.lower()
            break
    
    needs_calc = any(word in user_request for word in ["calculate", "math", "*", "+", "/", "-", "100/3"])
    
    if state.get("weather_done") and needs_calc and not state.get("calc_done"):
        print("  [Router] Weather done, routing to calculator")
        return "calculator_agent"
    
    print("  [Router] All tasks done, finishing")
    return END


# ============================================================
# Main
# ============================================================


def main() -> None:
    """Main function"""
    print("=" * 70)
    print("LangGraph Multi-Agent Demo (Simplified)")
    print("=" * 70)
    print(f"\nURL: {BASE_URL}")
    print(f"Model: {MODEL}\n")
    
    # Step 1: Create agents
    print("\n[Step 1] Creating Specialized Agents\n")
    weather = create_weather_node()
    calc = create_calculator_node()
    print("Created: Weather Agent, Calculator Agent\n")
    
    # Step 2: Build graph
    print("[Step 2] Building Workflow Graph\n")
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("weather_agent", weather["node"])
    workflow.add_node("weather_tools", weather["tools"])
    workflow.add_node("weather_done", weather["after_tools"])
    workflow.add_node("calculator_agent", calc["node"])
    workflow.add_node("calculator_tools", calc["tools"])
    workflow.add_node("calculator_done", calc["after_tools"])
    
    print("Nodes added: weather_agent, calculator_agent\n")
    
    # Step 3: Add edges
    print("[Step 3] Adding Edges\n")
    
    # START -> weather_agent (always start with weather)
    workflow.add_edge(START, "weather_agent")
    
    # Weather agent routing
    workflow.add_conditional_edges(
        "weather_agent",
        route_weather,
        {
            "weather_tools": "weather_tools",
            "weather_done": "weather_done",
        }
    )
    
    # After weather tools, back to weather agent
    workflow.add_edge("weather_tools", "weather_agent")
    
    # After weather done, decide whether to continue
    workflow.add_conditional_edges(
        "weather_done",
        should_continue,
        {
            "calculator_agent": "calculator_agent",
            END: END,
        }
    )
    
    # Calculator agent routing
    workflow.add_conditional_edges(
        "calculator_agent",
        route_calculator,
        {
            "calculator_tools": "calculator_tools",
            "calculator_done": "calculator_done",
        }
    )
    
    # After calculator tools, back to calculator agent
    workflow.add_edge("calculator_tools", "calculator_agent")
    
    # After calculator done, finish
    workflow.add_edge("calculator_done", END)
    
    print("Edges configured\n")
    
    # Step 4: Compile
    print("[Step 4] Compiling Graph\n")
    app = workflow.compile()
    print("Graph compiled successfully!\n")
    
    # Step 5: Print Graph Structure
    print("=" * 70)
    print("[Step 5] Graph Structure Visualization")
    print("=" * 70)
    
    # 方式 1：ASCII 字符图（无需额外依赖）
    print("\n📊 ASCII Graph：")
    print("-" * 70)
    try:
        print(app.get_graph().draw_ascii())
    except Exception as e:
        print(f"  (ASCII graph not available: {e})")
    
    # 方式 2：Mermaid 格式（可粘贴到 https://mermaid.live 查看）
    print("\n📊 Mermaid Graph (paste to https://mermaid.live to view)：")
    print("-" * 70)
    try:
        mermaid_code = app.get_graph().draw_mermaid()
        print(mermaid_code)
    except Exception as e:
        print(f"  (Mermaid graph not available: {e})")
    
    # 方式 3：获取图对象（可用于进一步处理）
    print("\n📊 Graph Nodes and Edges：")
    print("-" * 70)
    try:
        graph = app.get_graph()
        print(f"  Nodes: {list(graph.nodes.keys())}")
        print(f"  Edges: {[(e.source, e.target) for e in graph.edges]}")
    except Exception as e:
        print(f"  (Graph info not available: {e})")
    
    print("\n" + "=" * 70)
    
    # Step 6: Run tests
    print("=" * 70)
    print("[Step 6] Running Tests")
    print("=" * 70)
    
    # Test 1: Weather only
    print("\n" + "-" * 70)
    print("Test 1: Weather Query (Single Agent)\n")
    print("User: What's the weather in Beijing?\n")
    
    result = app.invoke(
        {"messages": [HumanMessage(content="What's the weather in Beijing?")], "weather_done": False, "calc_done": False},
        config={"recursion_limit": 10}
    )
    
    print("\nExecution Process:")
    for i, msg in enumerate(result["messages"]):
        if isinstance(msg, HumanMessage):
            print(f"  {i+1}. Human: {msg.content}")
        elif isinstance(msg, AIMessage):
            if msg.content:
                print(f"  {i+1}. AI: {msg.content}")
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  {i+1}. Tool Call: {tc['name']}({tc['args']})")
        elif isinstance(msg, ToolMessage):
            print(f"  {i+1}. Tool Result: {msg.content}")
    
    final = result["messages"][-1]
    print(f"\nAnswer: {final.content}\n")
    
    # Test 2: Math only (still goes through weather first, but weather won't call tools)
    print("-" * 70)
    print("\nTest 2: Math Calculation (Single Agent)\n")
    print("User: Calculate 15 * 37\n")
    
    result = app.invoke(
        {"messages": [HumanMessage(content="Calculate 15 * 37")], "weather_done": False, "calc_done": False},
        config={"recursion_limit": 10}
    )
    
    print("\nExecution Process:")
    for i, msg in enumerate(result["messages"]):
        if isinstance(msg, HumanMessage):
            print(f"  {i+1}. Human: {msg.content}")
        elif isinstance(msg, AIMessage):
            if msg.content:
                print(f"  {i+1}. AI: {msg.content}")
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  {i+1}. Tool Call: {tc['name']}({tc['args']})")
        elif isinstance(msg, ToolMessage):
            print(f"  {i+1}. Tool Result: {msg.content}")
    
    final = result["messages"][-1]
    print(f"\nAnswer: {final.content}\n")
    
    # Test 3: Multi-Agent collaboration
    print("-" * 70)
    print("\nTest 3: Multi-Agent Collaboration\n")
    print("User: What's Beijing's temperature? If >20, calculate 100/3\n")
    
    result = app.invoke(
        {"messages": [HumanMessage(content="What's Beijing's temperature? If >20, calculate 100/3")], "weather_done": False, "calc_done": False},
        config={"recursion_limit": 30}
    )
    
    print("\nExecution Process:")
    for i, msg in enumerate(result["messages"]):
        if isinstance(msg, HumanMessage):
            print(f"  {i+1}. Human: {msg.content}")
        elif isinstance(msg, AIMessage):
            if msg.content:
                print(f"  {i+1}. AI: {msg.content}")
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  {i+1}. Tool Call: {tc['name']}({tc['args']})")
        elif isinstance(msg, ToolMessage):
            print(f"  {i+1}. Tool Result: {msg.content}")
    
    final = result["messages"][-1]
    print(f"\nAnswer: {final.content}\n")
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print("\nLangGraph Multi-Agent Key Concepts:")
    print("1. Sequential Execution: Weather -> Calculator -> Finish")
    print("2. Conditional Routing: Based on state and user request")
    print("3. State Management: Track completion with boolean flags")
    print("4. Simple Architecture: No complex supervisor logic")
    print("\nAdvantages:")
    print("   - No recursion issues")
    print("   - Easy to understand and debug")
    print("   - Predictable execution flow")
    print("\nGraph Visualization:")
    print("   - ASCII Graph: app.get_graph().draw_ascii()")
    print("   - Mermaid Graph: app.get_graph().draw_mermaid()")
    print("   - Use https://mermaid.live to view Mermaid diagram")
    print("\nDone!\n")


if __name__ == "__main__":
    main()
