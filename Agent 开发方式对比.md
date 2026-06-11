# Agent 开发方式对比

本目录包含三种不同的 Agent 开发方式，从底层到高层封装，帮助您理解 Agent 的实现原理和不同框架的使用方法。

## 项目结构

```
mcp-demo-all/
├── simple-agent-demo/   # 手写 Agent（从零实现）
├── langchain-demo/      # 使用 LangChain 1.x 框架
├── langgraph-demo/      # 使用 LangGraph 框架
└── COMPARISON.md        # 本文档（对比三种方式）
```

## 三种开发方式对比

### 1. simple-agent-demo（手写 Agent）

**目录**: `/Users/berton/prj/mcp-demo-all/simple-agent-demo/`

**特点**:
- ✅ **从零实现**：完全手写 Agentic Loop（调用循环）
- ✅ **深度理解**：可以清楚看到 Agent 的每个细节
- ✅ **完全控制**：可以自定义任何行为
- ✅ **Mock 模式**：支持 `--mock` 参数，无需真实 API 即可运行演示
- ❌ **代码量大**：需要实现所有细节（含 Mock 约 493 行）
- ❌ **容易出错**：需要自己处理各种边界情况

**核心代码**:
```python
# 手写 Agentic Loop（run 方法）
def run(self, user_input: str) -> str:
    round_count = 0
    while round_count < self.max_rounds:
        round_count += 1
        # 1. 调用 LLM
        response = self.call_llm(user_input)

        # 2. 检查是否需要调用工具
        tool_calls = response.get("tool_calls")
        if not tool_calls:
            # 3. 无工具调用 → 返回最终回答
            return response.get("content", "")

        # 4. 有工具调用 → 遍历执行
        for tool_call in tool_calls:
            tool_result = self.execute_tool(tool_call)
            # 5. 将结果添加到对话历史
            self.conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result,
            })
        # 6. 继续循环

    return "⚠️ 已达到最大调用轮数，强制结束。"
```

**运行方式**:
```bash
# 真实 API 模式
python agent.py

# Mock 模式（无需 API，适合演示和学习）
python agent.py --mock
```

**适用场景**:
- 学习 Agent 原理
- 需要完全定制化的 Agent
- 对性能有极致要求

---

### 2. langchain-demo（使用 LangChain 1.x 框架）

**目录**: `/Users/berton/prj/mcp-demo-all/langchain-demo/`

**特点**:
- ✅ **快速开发**：使用 `create_agent` 一行代码创建 Agent
- ✅ **社区支持**：LangChain 有庞大的社区和丰富的文档
- ✅ **集成丰富**：与各种 LLM、向量数据库、工具集成良好
- ✅ **基于 LangGraph**：底层使用 LangGraph，获得状态管理能力
- ✅ **执行过程可视化**：`print_execution_process()` 可打印完整消息历史
- ❌ **框架依赖**：需要学习 LangChain 的 API
- ❌ **灵活性受限**：某些高度自定义需求可能难以实现

**核心代码**:
```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

# 1. 定义工具
@tool
def get_weather_tool(city: str) -> str:
    """获取指定城市的天气信息"""
    return get_weather(city)

# 2. 创建 LLM
llm = ChatOpenAI(api_key=API_KEY, base_url=BASE_URL, model=MODEL)

# 3. 创建 Agent（一行代码！底层是 LangGraph CompiledStateGraph）
agent = create_agent(
    model=llm,
    tools=[get_weather_tool],
    system_prompt="你是一个有帮助的助手"
)

# 4. 执行 Agent
result = agent.invoke({"messages": [("human", "北京天气怎么样？")]})

# 5. 打印执行过程（事后解读消息历史）
for msg in result["messages"]:
    if isinstance(msg, AIMessage):
        ...  # 解读 AI 决策步骤
    elif isinstance(msg, ToolMessage):
        ...  # 解读工具执行结果
```

**适用场景**:
- 快速构建标准 Agent
- 需要使用 LangChain 生态的工具和集成
- 不太复杂的 Agent 需求

---

### 3. langgraph-demo（使用 LangGraph 框架）

**目录**: `/Users/berton/prj/mcp-demo-all/langgraph-demo/`

**特点**:
- ✅ **细粒度控制**：可以精确控制 Agent 的每个步骤
- ✅ **复杂流程支持**：轻松实现循环、条件分支、并行等复杂流程
- ✅ **图结构可视化**：支持 ASCII 图和 Mermaid 格式两种方式打印 Graph 结构
- ✅ **执行过程可视化**：`print_execution_process()` 可打印完整消息历史
- ✅ **调试友好**：可以打印每个节点的输入和输出
- ✅ **持久化支持**：可以将状态保存到数据库
- ❌ **学习曲线较陡**：需要理解状态、节点、边等概念
- ❌ **代码量较多**：相比 LangChain 的 create_agent，需要写更多代码

**核心代码**:
```python
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage

# 1. 定义状态
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# 2. 定义节点函数
def call_model(state: AgentState):
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 3. 构建图
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

# 4. 添加边
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")
workflow.add_edge("agent", END)

# 5. 编译图
app = workflow.compile()

# 6. 打印 Graph 结构（两种方式）
print(app.get_graph().draw_ascii())    # ASCII 字符图
print(app.get_graph().draw_mermaid())  # Mermaid 格式（可粘贴到 mermaid.live）

# 7. 执行
result = app.invoke({"messages": [("human", "北京天气怎么样？")]})
```

**适用场景**:
- 复杂的多步骤任务
- 需要有条件分支的任务
- 需要循环的任务
- 需要并行执行的任务
- 需要状态持久化的任务

---

## 三者的层次关系

```
simple-agent-demo（手写 while 循环）
    ↓ 加上：回调、重试、流式、中间步骤记录
LangChain AgentExecutor（命令式封装，底层基于 LangGraph）
    ↓ 加上：状态持久化、并行节点、人工介入、子图
LangGraph CompiledStateGraph（图结构执行引擎）
```

> **理解关系**：`simple-agent-demo` 的 `run()` 方法揭示了 LangChain AgentExecutor 最核心的思想（LLM 决策 → 工具执行 → 循环），是理解两个框架的最好起点。LangChain 1.x 的 `create_agent` 底层直接返回 LangGraph 的 `CompiledStateGraph`，因此 LangGraph 是 LangChain 的底层引擎。

---

## 详细对比表

| 特性 | simple-agent-demo | langchain-demo | langgraph-demo |
|------|-------------------|----------------|----------------|
| **实现方式** | 手写 Agentic Loop | 使用 `create_agent` | 使用 `StateGraph` |
| **代码量** | 多（~493 行，含 Mock） | 少（~268 行） | 中（~358 行） |
| **学习曲线** | 陡（需要理解原理） | 缓（框架封装好） | 中（需要理解图、状态） |
| **灵活性** | 高（完全控制） | 中（框架限制） | 高（细粒度控制） |
| **复杂流程支持** | 难（需要手写） | 中（框架支持） | 易（图结构天然支持） |
| **调试难度** | 易（代码透明） | 难（封装较深） | 中（可以打印节点状态） |
| **Mock 模式** | ✅ 支持（`--mock`） | ❌ 不支持 | ❌ 不支持 |
| **图可视化** | ❌ 不支持 | ❌ 不支持 | ✅ ASCII + Mermaid |
| **执行过程打印** | ✅ 内联打印 | ✅ `print_execution_process()` | ✅ `print_execution_process()` |
| **社区支持** | 无 | 强（LangChain 社区） | 中（LangGraph 社区） |
| **适用场景** | 学习、高度定制化 | 快速开发标准 Agent | 复杂、有状态的 Agent |

---

## 如何选择？

### 选择 simple-agent-demo（手写 Agent）如果：

1. **您想深入学习 Agent 原理**：通过手写 Agentic Loop，您可以清楚看到 Agent 的每个细节
2. **您需要完全定制化的 Agent**：某些特殊需求可能无法通过框架满足
3. **您对性能有极致要求**：手写代码可以避免框架带来的额外开销
4. **您需要在无 API 环境下演示**：使用 `--mock` 模式即可运行

### 选择 langchain-demo（LangChain 框架）如果：

1. **您需要快速开发**：使用 `create_agent` 一行代码即可创建 Agent
2. **您需要使用 LangChain 生态**：LangChain 有丰富的集成（LLM、向量数据库、工具等）
3. **您的 Agent 需求不太复杂**：标准 Agent 流程（LLM → Tools → LLM）就能满足需求

### 选择 langgraph-demo（LangGraph 框架）如果：

1. **您的任务复杂，需要多步骤**：例如，需要先查询数据库，然后进行计算，最后生成报告
2. **您需要有条件分支**：例如，根据中间结果决定下一步操作
3. **您需要循环**：例如，需要重复执行某些步骤直到满足条件
4. **您需要并行执行**：例如，某些步骤可以同时进行
5. **您需要状态持久化**：例如，需要将 Agent 状态保存到数据库，以便长时间运行
6. **您需要可视化工作流**：使用 `draw_ascii()` 或 `draw_mermaid()` 查看图结构

---

## 运行示例

### 1. 运行 simple-agent-demo

```bash
cd simple-agent-demo
source venv/bin/activate

# 真实 API 模式
python agent.py

# Mock 模式（无需 API）
python agent.py --mock
```

### 2. 运行 langchain-demo

```bash
cd langchain-demo
source venv/bin/activate
python agent.py
```

### 3. 运行 langgraph-demo

```bash
cd langgraph-demo
source venv/bin/activate
python agent.py
```

---

## API 配置

所有三个 demo 都使用相同的 Venus 平台 API 配置：

```python
# Venus 平台 API 配置（腾讯内部 LLM 代理服务）
API_KEY: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
BASE_URL: str = "http://v2.open.venus.oa.com/llmproxy"
MODEL: str = "gpt-4o-mini"
```

---

## 总结

1. **simple-agent-demo** 适合学习 Agent 原理，帮助您理解 Agent 的底层工作机制；新增 `--mock` 模式，无需 API 即可运行
2. **langchain-demo** 适合快速开发标准 Agent，利用 LangChain 的生态和社区支持；新增执行过程打印，方便调试
3. **langgraph-demo** 适合构建复杂的、有状态的、多步骤的 Agent，提供细粒度的控制；新增 ASCII 和 Mermaid 两种图结构可视化

**推荐学习路径**：
1. 先学习 `simple-agent-demo`，理解 Agent 的基本原理（可用 `--mock` 模式快速上手）
2. 然后学习 `langchain-demo`，掌握快速开发 Agent 的方法
3. 最后学习 `langgraph-demo`，应对复杂的 Agent 开发需求，并通过图可视化理解工作流

---

## 参考资料

- [LangChain 官方文档](https://python.langchain.com/)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [Venus 平台文档](https://iwiki.woa.com/p/4009937875)
- [Mermaid 在线预览](https://mermaid.live)
