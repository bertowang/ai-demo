# Simple Agent Demo

最简单的 Agent 实现，适合理解 Agent 的核心概念。

## 功能特性

本 demo 展示一个最基础的 Agent，包含：

1. **调用 LLM（决策中枢）** - 使用 OpenAI API
2. **工具调用能力（Function Calling）** - 支持天气查询和数学计算
3. **Agentic Loop（自主循环）** - 不断调用模型直到返回最终答案
4. **上下文管理（记忆）** - 维护完整的对话历史

## 文件结构

```
simple-agent-demo/
├── agent.py          # Agent 主文件（完整可运行）
└── README.md         # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python3.12 -m venv venv
source venv/bin/activate

# 安装依赖
pip install openai
```

### 2. 运行 demo

#### 方式 1：模拟模式（推荐，不需要 OpenAI API）

```bash
python agent.py --mock
```

模拟模式会模拟 LLM 的响应，适合：
- 学习 Agent 的工作原理
- 测试代码逻辑
- 没有 OpenAI API key 的情况

#### 方式 2：真实 API 模式（需要 OpenAI API）

```bash
python agent.py
```

真实模式会调用 OpenAI API，适合：
- 体验真实的 LLM 决策
- 测试工具调用
- 有 OpenAI API key 的情况

**注意**：如果您看到 `RateLimitError` 或 `insufficient_quota` 错误，程序会自动切换到模拟模式。

## 代码示例

### 最简单的使用方式

```python
from agent import SimpleAgent

# 创建 Agent 实例
agent: SimpleAgent = SimpleAgent()

# 运行 Agent
answer: str = agent.run("请帮我查询北京的天气")
print(answer)
```

### 核心类：SimpleAgent

```python
class SimpleAgent:
    """
    最简单的 Agent 实现

    核心能力：
    1. call_llm()      - 调用 LLM（决策）
    2. execute_tool()  - 执行工具（行动）
    3. run()           - Agentic Loop（自主循环）
    4. conversation_history - 上下文管理（记忆）
    """
```

## 核心概念

### 1. Agentic Loop（调用循环）

```
用户输入
    ↓
调用 LLM
    ↓
需要调用工具？
    ↓ 是
执行工具
    ↓
将结果加入上下文
    ↓
继续循环 ──────┘
    ↓ 否
返回最终回答
```

### 2. 工具调用（Function Calling）

Agent 可以调用两个工具：

- **get_weather(city)** - 查询天气
- **calculate(expression)** - 数学计算

LLM 会自动决定是否需要调用工具，以及调用哪个工具。

### 3. 上下文管理（记忆）

Agent 维护一个 `conversation_history` 列表，记录：

- 用户消息
- 助手回复
- 工具调用
- 工具结果

这使得 Agent 能够进行多轮对话。

## 与 harness-demo 的对比

| 特性 | simple-agent-demo | harness-demo |
|------|-------------------|--------------|
| **复杂度** | ⭐ 最简单 | ⭐⭐⭐ 完整实现 |
| **代码行数** | ~200 行 | ~500 行 |
| **适合人群** | 初学者 | 进阶开发者 |
| **功能** | 核心功能 | 完整功能 |
| **日志** | 简单打印 | 详细日志 |
| **权限控制** | ❌ 无 | ✅ 有 |
| **沙箱** | ❌ 无 | ✅ 有 |

## 学习路径

推荐学习顺序：

1. **simple-agent-demo** - 理解 Agent 的核心概念
2. **harness-demo** - 学习完整的 Harness 实现
3. **stdio-demo** - 学习 MCP Server 开发
4. **http-demo** - 学习 HTTP MCP Server 开发

## 扩展建议

您可以尝试扩展这个 demo：

1. 添加更多工具（例如：文件读写、网络搜索）
2. 添加日志记录（参考 harness-demo）
3. 添加权限控制（参考 harness-demo）
4. 改造成 MCP Server（参考 harness_mcp_server.py）

## 常见问题

### Q: 为什么选择 gpt-4o-mini？

A: gpt-4o-mini 是 OpenAI 最便宜的模型，适合演示和测试。

### Q: 如何更换模型？

A: 修改 `MODEL` 常量：

```python
MODEL: str = "gpt-4o"  # 或其他支持 Function Calling 的模型
```

### Q: 如何添加新工具？

A: 三步：

1. 定义工具函数
2. 添加到 `TOOL_REGISTRY`
3. 添加到 `TOOLS_SCHEMA`

示例：

```python
# 1. 定义工具函数
def read_file(path: str) -> str:
    """读取文件"""
    with open(path, "r") as f:
        return f.read()

# 2. 添加到 TOOL_REGISTRY
TOOL_REGISTRY["read_file"] = read_file

# 3. 添加到 TOOLS_SCHEMA
TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读取文件内容",
        "parameters": {...},
    },
})
```

## 作者

Berton

## 日期

2026-06-10
