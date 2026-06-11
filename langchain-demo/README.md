# LangChain Demo

使用 LangChain 1.x 框架构建 Agent 的完整示例。

## 功能特性

本 demo 展示如何使用 LangChain 1.x 框架构建 Agent：

1. **使用 ChatOpenAI 调用 LLM**（通过 Venus 平台）
2. **定义工具（Tools）**供 Agent 使用（使用 @tool 装饰器）
3. **使用 create_agent 创建 Agent**（LangChain 1.x 新 API）
4. **展示完整的 Agent 工作流程**

> **注意**：本 demo 使用 LangChain 1.x 版本，其中 `create_agent` 是直接返回 LangGraph `CompiledStateGraph` 的新 API。

## 环境配置

### 1. 创建虚拟环境（推荐）

```bash
cd langchain-demo
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
LangChain Demo - 使用 LangChain 1.x 构建 Agent
============================================================

【步骤 1】定义工具
✅ 已定义 2 个工具：
   - get_weather_tool: 获取指定城市的天气信息
   - calculate_tool: 执行数学表达式计算

【步骤 2】创建 LLM（大语言模型）
✅ 已创建 LLM：gpt-4o-mini

【步骤 3】使用 create_agent 创建 Agent（LangChain 1.x 新 API）
✅ 已创建 Agent（使用 create_agent）
    create_agent 直接返回一个编译好的 LangGraph CompiledStateGraph

【步骤 4】执行 Agent
📝 测试 1：查询天气
✅ 最终回答：北京的天气是晴天，气温为25°C。

...
```

## 代码架构

### 核心组件（LangChain 1.x）

| 组件 | 说明 | LangChain 1.x API |
|------|------|---------------|
| **Tools（工具）** | 定义 Agent 可以使用的工具 | `@tool` 装饰器 |
| **LLM（大语言模型）** | 负责决策和生成回答 | `ChatOpenAI` |
| **create_agent** | 创建 Agent（新 API） | `langchain.agents.create_agent` |
| **agent.invoke()** | 执行 Agent | `CompiledStateGraph.invoke()` |

### 执行流程

```
用户输入（messages）
    ↓
create_agent() 创建 Agent
    ↓
agent.invoke() 执行
    ↓
LLM 决策：是否需要调用工具？
    ↓
是 → 调用工具 → 将结果返回给 LLM → 生成最终回答
否 → 直接生成回答
    ↓
最终回答
```

## LangChain 1.x 核心概念

### 1. @tool 装饰器

```python
from langchain.tools import tool

@tool
def my_tool(param: str) -> str:
    """工具描述（LLM 会看到这个）"""
    return "结果"
```

### 2. ChatOpenAI

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    api_key="your_api_key",
    base_url="https://api.example.com",
    model="gpt-4o-mini",
    temperature=0.7,
)
```

### 3. create_agent（新 API）

```python
from langchain.agents import create_agent

agent = create_agent(
    model=llm,  # 或字符串 "openai:gpt-4o-mini"
    tools=tools,
    system_prompt="你是一个有帮助的助手",
)
# agent 是一个 CompiledStateGraph，可以直接调用
result = agent.invoke({"messages": [("human", "你好")]})
```

### 4. 执行 Agent

```python
result = agent.invoke({
    "messages": [("human", "请帮我查询北京的天气")]
})

# 获取最终回答（最后一个 AI 消息）
final_message = result["messages"][-1]
print(final_message.content)
```

## LangChain 1.x 与旧版本（0.x）的对比

| 特性 | LangChain 0.x | LangChain 1.x |
|------|---------------|--------------|
| **创建 Agent** | `create_tool_calling_agent` | `create_agent` |
| **执行 Agent** | `AgentExecutor` | 直接返回 `CompiledStateGraph` |
| **底层实现** | 自定义循环 | 基于 LangGraph |
| **状态管理** | 隐式 | 显式（使用 messages 状态） |
| **灵活性** | 中 | 高（可利用 LangGraph 的所有功能） |

## 与 LangGraph 的对比

| 特性 | LangChain 1.x | LangGraph |
|------|----------------|-----------|
| **抽象级别** | 高（封装好的 Agent） | 中（更细粒度的控制） |
| **状态管理** | 隐式（内部使用 LangGraph） | 显式（使用 TypedDict 定义） |
| **工作流程** | 固定（Agent → Tools → Agent） | 灵活（自己定义节点和边） |
| **复杂度** | 低（API 简单） | 中（需要理解图、状态等概念） |
| **适用场景** | 快速构建标准 Agent | 构建复杂的、有状态的、多步骤的 Agent |

## 优势

1. **快速开发**：框架提供了成熟的 Agent 实现，无需从头手写
2. **社区支持**：LangChain 有庞大的社区和丰富的文档
3. **可扩展性强**：可以轻松添加新的工具和功能
4. **集成丰富**：与各种 LLM、向量数据库、工具集成良好
5. **基于 LangGraph**：底层使用 LangGraph，可以获得状态管理和复杂流程的能力

## 局限性

1. **框架依赖**：需要学习 LangChain 的 API 和概念
2. **灵活性受限**：某些自定义需求可能难以实现
3. **调试困难**：框架封装较深，调试时可能难以定位问题

## 参考资料

- [LangChain 官方文档](https://python.langchain.com/)
- [LangChain Agents 文档](https://docs.langchain.com/oss/python/langchain/agents)
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [Venus 平台文档](https://iwiki.woa.com/p/4009937875)

## 许可证

MIT License
