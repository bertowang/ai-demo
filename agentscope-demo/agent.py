"""
AgentScope 多 Agent 协作 Demo

AgentScope 是阿里巴巴开源的多 Agent 框架，核心特点：
1. 以"消息"为核心的 Agent 间通信
2. 内置多种 Agent 类型（对话、用户代理、React Agent 等）
3. 灵活的 Pipeline 编排（顺序、条件、循环、并行）
4. 支持分布式部署

本 Demo 展示：
- 基本 Agent 创建与对话
- 多 Agent 协作（Pipeline 编排）
- 自定义工具（ServiceToolkit）
- 与 LangGraph 多 Agent 方案的对比

依赖：pip install agentscope
"""

import os
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import agentscope
from agentscope.agents import DialogAgent, ReActAgent
from agentscope.message import Msg
from agentscope.pipelines import sequentialpipeline, ifelsepipeline
from agentscope.service import ServiceToolkit, ServiceResponse, ServiceExecStatus


# ============================================================
# 第一步：定义自定义工具（类似 MCP 工具）
# ============================================================

def get_weather(city: str) -> ServiceResponse:
    """查询指定城市的天气信息

    Args:
        city (str): 城市名称，如 "北京"、"上海"

    Returns:
        ServiceResponse: 天气查询结果
    """
    # 模拟天气数据
    weather_data = {
        "北京": {"temp": "28°C", "condition": "晴", "humidity": "45%"},
        "上海": {"temp": "32°C", "condition": "多云", "humidity": "78%"},
        "广州": {"temp": "35°C", "condition": "雷阵雨", "humidity": "85%"},
        "深圳": {"temp": "33°C", "condition": "阴", "humidity": "80%"},
    }

    if city in weather_data:
        data = weather_data[city]
        result = f"{city}天气：{data['condition']}，温度 {data['temp']}，湿度 {data['humidity']}"
        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=result
        )
    else:
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content=f"未找到城市 '{city}' 的天气数据，支持的城市：{list(weather_data.keys())}"
        )


def calculate(expression: str) -> ServiceResponse:
    """计算数学表达式

    Args:
        expression (str): 数学表达式，如 "2 + 3 * 4"

    Returns:
        ServiceResponse: 计算结果
    """
    try:
        # 安全计算（仅允许数学运算）
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content=f"不安全的表达式：{expression}"
            )
        result = eval(expression)
        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=f"{expression} = {result}"
        )
    except Exception as e:
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content=f"计算错误：{str(e)}"
        )


# ============================================================
# 第二步：初始化 AgentScope
# ============================================================

def init_agentscope():
    """初始化 AgentScope 框架"""

    # 模型配置（使用 OpenAI 兼容接口）
    model_configs = [
        {
            "config_name": "gpt4o_mini",
            "model_type": "openai_chat",
            "model_name": "gpt-4o-mini",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "generate_args": {
                "temperature": 0.7,
            }
        }
    ]

    # 如果配置了自定义 base_url，添加到配置中
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        model_configs[0]["client_args"] = {"base_url": base_url}

    # 初始化
    agentscope.init(
        model_configs=model_configs,
        project="agentscope-demo",
        save_log=True,
    )
    print("✅ AgentScope 初始化完成\n")


# ============================================================
# 第三步：Demo 1 - 基本对话 Agent
# ============================================================

def demo_basic_dialog():
    """
    Demo 1：基本对话 Agent

    DialogAgent 是最简单的 Agent 类型：
    - 接收一条消息
    - 调用 LLM 生成回复
    - 返回回复消息

    类比：相当于 simple-agent-demo 中没有工具的纯对话模式
    """
    print("=" * 60)
    print("Demo 1: 基本对话 Agent")
    print("=" * 60)

    # 创建一个对话 Agent
    assistant = DialogAgent(
        name="小助手",
        model_config_name="gpt4o_mini",
        sys_prompt="你是一个友好的AI助手，回答简洁明了，用中文回复。",
    )

    # 发送消息并获取回复
    user_msg = Msg(name="用户", content="请用一句话解释什么是 Agent？", role="user")
    print(f"👤 用户: {user_msg.content}")

    response = assistant(user_msg)
    print(f"🤖 小助手: {response.content}")
    print()

    return response


# ============================================================
# 第四步：Demo 2 - 带工具的 ReAct Agent
# ============================================================

def demo_react_agent():
    """
    Demo 2：带工具的 ReAct Agent

    ReActAgent 实现了 ReAct（Reasoning + Acting）模式：
    - 思考（Thought）：分析当前情况
    - 行动（Action）：调用工具
    - 观察（Observation）：获取工具结果
    - 循环直到得出最终答案

    类比：
    - 相当于 simple-agent-demo 的 Agentic Loop
    - 相当于 langgraph-demo 的 agent → tools → agent 循环
    """
    print("=" * 60)
    print("Demo 2: ReAct Agent（带工具调用）")
    print("=" * 60)

    # 创建工具包
    toolkit = ServiceToolkit()
    toolkit.add(get_weather)
    toolkit.add(calculate)

    # 创建 ReAct Agent（自带 Agentic Loop）
    react_agent = ReActAgent(
        name="智能助手",
        model_config_name="gpt4o_mini",
        sys_prompt="你是一个智能助手，可以查询天气和进行数学计算。请用中文回复。",
        service_toolkit=toolkit,
        max_iters=5,  # 最大推理轮次
        verbose=True,  # 打印推理过程
    )

    # 测试 1：天气查询
    print("\n--- 测试 1：天气查询 ---")
    msg1 = Msg(name="用户", content="北京今天天气怎么样？", role="user")
    print(f"👤 用户: {msg1.content}")
    response1 = react_agent(msg1)
    print(f"🤖 智能助手: {response1.content}\n")

    # 测试 2：数学计算
    print("\n--- 测试 2：数学计算 ---")
    msg2 = Msg(name="用户", content="请计算 (15 + 27) * 3 的结果", role="user")
    print(f"👤 用户: {msg2.content}")
    response2 = react_agent(msg2)
    print(f"🤖 智能助手: {response2.content}\n")

    # 测试 3：组合任务
    print("\n--- 测试 3：组合任务 ---")
    msg3 = Msg(name="用户", content="查一下上海的天气，然后帮我算一下 32 * 1.8 + 32 是多少华氏度", role="user")
    print(f"👤 用户: {msg3.content}")
    response3 = react_agent(msg3)
    print(f"🤖 智能助手: {response3.content}\n")

    return response3


# ============================================================
# 第五步：Demo 3 - 多 Agent Pipeline 协作
# ============================================================

def demo_multi_agent_pipeline():
    """
    Demo 3：多 Agent Pipeline 协作

    AgentScope 的 Pipeline 编排方式：
    - sequentialpipeline：顺序执行（A → B → C）
    - ifelsepipeline：条件分支（if 条件 then A else B）
    - whilelooppipeline：循环执行
    - parallelpipeline：并行执行

    本 Demo 展示：翻译 Agent → 润色 Agent → 审核 Agent 的流水线

    类比：
    - 相当于 langgraph-multi-agent-demo 的多节点串联
    - 但 AgentScope 的 Pipeline 语法更简洁直观
    """
    print("=" * 60)
    print("Demo 3: 多 Agent Pipeline 协作")
    print("=" * 60)

    # Agent 1：翻译 Agent
    translator = DialogAgent(
        name="翻译官",
        model_config_name="gpt4o_mini",
        sys_prompt=(
            "你是一个专业翻译，将用户输入的中文翻译成英文。"
            "只输出翻译结果，不要添加任何解释。"
        ),
    )

    # Agent 2：润色 Agent
    polisher = DialogAgent(
        name="润色师",
        model_config_name="gpt4o_mini",
        sys_prompt=(
            "你是一个英文润色专家。接收一段英文文本，对其进行润色优化，"
            "使其更加地道、流畅。只输出润色后的结果。"
        ),
    )

    # Agent 3：审核 Agent
    reviewer = DialogAgent(
        name="审核员",
        model_config_name="gpt4o_mini",
        sys_prompt=(
            "你是一个翻译质量审核员。接收一段英文翻译，评估其质量，"
            "给出评分（1-10分）和简短评语。格式：\n"
            "评分：X/10\n评语：..."
        ),
    )

    # 使用 sequentialpipeline 串联三个 Agent
    user_msg = Msg(
        name="用户",
        content="人工智能正在深刻改变我们的生活方式，从智能家居到自动驾驶，无处不在。",
        role="user"
    )
    print(f"👤 用户（原文）: {user_msg.content}\n")

    # 顺序执行：翻译 → 润色 → 审核
    # sequentialpipeline 会将前一个 Agent 的输出作为下一个 Agent 的输入
    result = sequentialpipeline(
        operators=[translator, polisher, reviewer],
        x=user_msg,
    )

    print(f"\n📋 最终审核结果: {result.content}")
    print()

    return result


# ============================================================
# 第六步：Demo 4 - 条件分支 Pipeline
# ============================================================

def demo_conditional_pipeline():
    """
    Demo 4：条件分支 Pipeline

    使用 ifelsepipeline 实现条件路由：
    - 根据用户输入内容，决定交给哪个 Agent 处理
    - 类似 langgraph-multi-agent-demo 中的 Supervisor 路由

    区别：
    - LangGraph：用 conditional_edges + 路由函数
    - AgentScope：用 ifelsepipeline + 条件函数
    """
    print("=" * 60)
    print("Demo 4: 条件分支 Pipeline")
    print("=" * 60)

    # 天气专家
    weather_expert = DialogAgent(
        name="天气专家",
        model_config_name="gpt4o_mini",
        sys_prompt="你是天气专家，回答天气相关问题。如果问题不是关于天气的，说'这不是我的专业领域'。用中文回复。",
    )

    # 数学专家
    math_expert = DialogAgent(
        name="数学专家",
        model_config_name="gpt4o_mini",
        sys_prompt="你是数学专家，回答数学计算相关问题。用中文回复。",
    )

    # 条件判断函数
    def is_weather_question(msg: Msg) -> bool:
        """判断是否是天气相关问题"""
        weather_keywords = ["天气", "温度", "下雨", "晴", "阴", "风", "气温"]
        return any(kw in msg.content for kw in weather_keywords)

    # 测试用例
    test_cases = [
        "北京明天天气怎么样？",
        "请帮我计算 123 * 456 等于多少？",
    ]

    for question in test_cases:
        msg = Msg(name="用户", content=question, role="user")
        print(f"\n👤 用户: {question}")

        # 条件分支：天气问题 → 天气专家，否则 → 数学专家
        result = ifelsepipeline(
            condition=is_weather_question,
            if_body=weather_expert,
            else_body=math_expert,
            x=msg,
        )
        agent_name = "天气专家" if is_weather_question(msg) else "数学专家"
        print(f"🤖 [{agent_name}]: {result.content}")

    print()
    return result


# ============================================================
# 主函数
# ============================================================

def main():
    """运行所有 Demo"""
    print("\n" + "🚀" * 30)
    print("   AgentScope 多 Agent 框架 Demo")
    print("🚀" * 30 + "\n")

    # 初始化
    init_agentscope()

    # 运行各个 Demo
    print("\n" + "─" * 60)
    print("  选择要运行的 Demo：")
    print("  1. 基本对话 Agent")
    print("  2. ReAct Agent（带工具调用）")
    print("  3. 多 Agent Pipeline 协作")
    print("  4. 条件分支 Pipeline")
    print("  0. 运行全部")
    print("─" * 60)

    choice = input("\n请输入选项 (0-4): ").strip()

    if choice == "1":
        demo_basic_dialog()
    elif choice == "2":
        demo_react_agent()
    elif choice == "3":
        demo_multi_agent_pipeline()
    elif choice == "4":
        demo_conditional_pipeline()
    elif choice == "0":
        demo_basic_dialog()
        demo_react_agent()
        demo_multi_agent_pipeline()
        demo_conditional_pipeline()
    else:
        print("无效选项，运行全部 Demo...")
        demo_basic_dialog()
        demo_react_agent()
        demo_multi_agent_pipeline()
        demo_conditional_pipeline()

    print("\n" + "✅" * 30)
    print("   所有 Demo 运行完成！")
    print("✅" * 30 + "\n")


if __name__ == "__main__":
    main()
