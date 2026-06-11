# LangGraph Demo

使用 LangGraph 框架构建有状态的多步骤 Agent。

## 功能特性

本 demo 展示如何使用 LangGraph 框架构建 Agent：

1. **使用 ChatOpenAI 调用 LLM**（通过 Venus 平台）
2. **定义工具（Tools）**供 Agent 使用（使用 @tool 装饰器）
3. **使用 StateGraph 定义 Agent 的工作流程**
4. **展示 LangGraph 的核心概念**：状态（State）、节点（Node）、边（Edge）
5. **展示有状态的多步骤 Agent**

## 环境配置

### 1. 创建虚拟环境（推荐）

```bash
cd langgraph-demo
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置说明

本 demo 使用腾讯内部 Venus 平台 API，配置已在 `agent.py` 中设置：

```python
API_KEY: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
BASE_URL: str = "http://v2.open.venus.oa.com/llmproxy"
MODEL: str = "gpt-4o-mini"
```

## 使用方法

### 运行 Demo

```bash
python agent.py
```

### 预期输出

```
============================================================
LangGraph Demo - 使用 LangGraph 构建 Agent
============================================================

【步骤 1】定义工具
✅ 已定义 2 个工具：
   - get_weather_tool: 获取指定城市的天气信息
   - calculate_tool: 执行数学表达式计算

【步骤 2】创建 LLM（大语言模型）
✅ 已创建 LLM：gpt-4o-mini
   已绑定 2 个工具

【步骤 3】定义 Agent 的状态
✅ 已定义 AgentState（使用 TypedDict）

【步骤 4】定义节点函数
✅ 已定义节点函数：
   - call_model: 调用 LLM
   - tool_node: 执行工具（使用 ToolNode）

【步骤 5】构建状态图（StateGraph）
✅ 已构建状态图
   节点：START → agent → tools → agent → END

【步骤 6】编译图（创建 Agent）
✅ 已编译图，创建 Agent

【步骤 7】执行 Agent
📝 测试 1：查询天气
✅ 最终回答：北京的天气是晴天，气温为25°C。

📊 执行过程：
  1. 用户：请帮我查询北京的天气
  2. AI（调用工具）：[{'name': 'get_weather_tool', ...}]
  3. 工具返回：晴天，25°C
  4. AI：北京的天气是晴天，气温为25°C。

...
```

## 代码架构

### 核心组件

| 组件 | 说明 | LangGraph API |
|------|------|---------------|
| **State（状态）** | 定义 Agent 的状态 | `TypedDict`, `Annotated` |
| **Nodes（节点）** | 定义每个步骤的执行逻辑 | `add_node()` |
| **Edges（边）** | 定义节点之间的流转 | `add_edge()`, `add_conditional_edges()` |
| **Graph（图）** | 使用 StateGraph 构建工作流程 | `StateGraph` |
| **Compile（编译）** | 将图编译为可执行的 Agent | `workflow.compile()` |

### 执行流程

```
用户输入（HumanMessage）
    ↓
START
    ↓
agent 节点（调用 LLM）
    ↓
有条件边：是否需要调用工具？
    ↓
是 → tools 节点（执行工具） → agent 节点（再次调用 LLM）
否 → END
    ↓
最终回答（AIMessage）
```

## LangGraph 核心概念

### 1. State（状态）

```python
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # add_messages 表示状态更新时，追加消息而不是替换
```

### 2. Nodes（节点）

```python
def call_model(state: AgentState) -> Dict[str, Any]:
    """调用 LLM 的节点函数"""
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 使用 ToolNode（预构建的工具执行节点）
from langgraph.prebuilt import ToolNode
tool_node = ToolNode(tools)
```

### 3. Edges（边）

```python
from langgraph.graph import START, END

# 普通边：从一个节点到另一个节点
workflow.add_edge(START, "agent")
workflow.add_edge("tools", "agent")
workflow.add_edge("agent", END)

# 条件边：根据条件决定下一个节点
from langgraph.prebuilt import tools_condition
workflow.add_conditional_edges(
    "agent",
    tools_condition,  # 如果有工具调用，去 tools；否则去 END
)
```

### 4. Graph（图）

```python
from langgraph.graph import StateGraph

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
# ... 添加边
app = workflow.compile()
```

### 5. 执行

```python
result = app.invoke({
    "messages": [HumanMessage(content="请帮我查询北京的天气")]
})
```

## 与 LangChain 1.x 的对比

| 特性 | LangChain 1.x | LangGraph |
|------|----------------|-----------|
| **抽象级别** | 高（封装好的 Agent） | 中（更细粒度的控制） |
| **状态管理** | 隐式（Agent 内部管理） | 显式（使用 TypedDict 定义） |
| **工作流程** | 固定（Agent → Tools → Agent） | 灵活（自己定义节点和边） |
| **复杂流程** | 难以实现（如循环、条件分支） | 容易实现（图结构天然支持） |
| **调试** | 较难（封装较深） | 容易（可以打印每个节点的状态） |
| **学习曲线** | 缓（API 简单） | 中（需要理解图、状态等概念） |

## 优势

1. **细粒度控制**：可以精确控制 Agent 的每个步骤
2. **复杂流程支持**：轻松实现循环、条件分支、并行等复杂流程
3. **状态可视化**：可以可视化 Agent 的工作流程（使用 `app.get_graph().draw_png()`）
4. **调试友好**：可以打印每个节点的输入和输出
5. **持久化支持**：可以将状态保存到数据库，实现长时间运行的 Agent

## 局限性

1. **学习曲线较陡**：需要理解状态、节点、边等概念
2. **代码量较多**：相比 LangChain 的 AgentExecutor，需要写更多代码
3. **过度灵活**：对于简单任务，可能过于复杂

## 适用场景

1. **复杂的多步骤任务**：需要多个步骤，且步骤之间有依赖关系
2. **有条件分支的任务**：需要根据中间结果决定下一步
3. **需要循环的任务**：需要重复执行某些步骤直到满足条件
4. **需要并行执行的任务**：某些步骤可以并行执行
5. **需要状态持久化的任务**：需要将 Agent 状态保存到数据库

## 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [Venus 平台文档](https://iwiki.woa.com/p/4009937875)

## 许可证

MIT License
