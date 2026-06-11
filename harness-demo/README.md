# Harness Demo - LLM 运行时支撑层演示

## 一句话理解

```
Harness = 模型的运行时支撑层（Runtime Scaffolding）
         = 把"会生成文本的模型"变成"能在真实世界里可靠完成任务的系统"

模型只做一件事：吃 token，吐 token
Harness 干的就是其余所有事
```

## 本 Demo 演示了 Harness 的哪些职责？

| Harness 职责 | 本 Demo 中的实现 |
|--------------|-----------------|
| **调用循环（Agentic Loop）** | `agent_loop()` 函数：不断循环调用模型 → 解析输出 → 执行工具 → 继续循环 |
| **工具路由与执行** | `execute_tool()` 函数：根据模型输出，路由到对应的工具函数并执行 |
| **上下文/记忆管理** | `conversation_history` 列表：维护对话历史，实现多轮对话 |
| **权限与沙箱** | `ALLOWED_DIRS` + `check_path_allowed()`：限制只能访问指定目录 |
| **验证与兜底** | `validate_tool_call()` 函数：检查工具调用是否合法，不合法则返回错误信息 |
| **观测与审计** | `log_step()` 函数：记录每一步的 token 消耗和工具调用链 |

## 快速开始

```bash
# 1. 进入目录
cd /Users/berton/prj/mcp-demo-all/harness-demo

# 2. 安装依赖
pip install openai

# 3. 设置 API Key（需要您自己有 OpenAI 或兼容 API）
export OPENAI_API_KEY="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"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 或您的兼容 API 地址

# 4. 运行 Demo
python harness.py
```

## 核心代码文件

```
harness-demo/
├── README.md          # 本文件
├── harness.py         # 核心 Harness 实现
└── test_harness.py   # 测试脚本
```

## 与您已学的 MCP 概念的关系

```
┌─────────────────────────────────────────────────┐
│          您已经理解的的概念                        │
│                                                 │
│  MCP Server = 提供工具的服务端                    │
│  MCP Client = 调用工具的客户端                    │
│                                                 │
│          本 Demo 展示的概念                        │
│                                                 │
│  Harness = 包裹模型的运行时支撑层                  │
│            = MCP Client 的更底层实现              │
│            = 负责「调用循环 + 工具路由 + 上下文管理」│
└─────────────────────────────────────────────────┘

关系：
  MCP Client 本身就是一个简化版的 Harness
  Harness 是更通用的概念，MCP 是 Harness 的一种实现方式
```

## 引用来源

本 Demo 的概念和设计受到以下资料的启发：
- Andrej Karpathy 对 Harness 的定义："The model is the engine. The harness is the rest of the car."
- 《Building Effective Agents》（Anthropic 官方 Agent 设计指南）
- 《A Practical Guide to Building Agentic Systems》（agents.kiln.ai）
