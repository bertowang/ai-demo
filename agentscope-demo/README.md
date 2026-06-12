# AgentScope Demo

> AgentScope 是阿里巴巴开源的多 Agent 框架，以"消息驱动 + Pipeline 编排"为核心设计理念。

## 核心概念

| 概念 | 说明 | 类比 |
|------|------|------|
| `Msg` | Agent 间通信的消息对象 | LangGraph 的 State |
| `DialogAgent` | 基本对话 Agent | LangChain 的 ChatModel |
| `ReActAgent` | 带工具的推理 Agent | LangGraph 的 agent+tools 循环 |
| `Pipeline` | Agent 编排方式 | LangGraph 的 Graph |
| `ServiceToolkit` | 工具注册管理 | MCP 的 @tool 装饰器 |

## 运行方式

```bash
cd agentscope-demo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python agent.py
```

## Demo 列表

1. **基本对话 Agent** — 最简单的 Agent，接收消息返回回复
2. **ReAct Agent** — 带工具调用的推理 Agent（思考→行动→观察循环）
3. **多 Agent Pipeline** — 翻译→润色→审核 流水线协作
4. **条件分支 Pipeline** — 根据问题类型路由到不同 Agent

## 与 LangGraph 的对比

| 特性 | AgentScope | LangGraph |
|------|-----------|-----------|
| 编排方式 | Pipeline 函数式 | Graph 图结构 |
| 学习曲线 | 较低（Python 函数风格） | 中等（需理解图概念） |
| 多 Agent 通信 | 消息传递（Msg） | 共享状态（State） |
| 条件路由 | `ifelsepipeline` | `conditional_edges` |
| 并行执行 | `parallelpipeline` | `Send()` API |
| 分布式 | 原生支持 | 需额外配置 |
| 生态 | 阿里系 | LangChain 生态 |
