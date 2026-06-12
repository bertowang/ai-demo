# mcp-demo-all 技术总览

> 本仓库通过一系列由浅入深的 Demo，覆盖了 AI 应用开发的核心技术栈。
> 建议按照下方的**技术演进顺序**学习，每个阶段都建立在前一阶段的基础之上。

---

## 技术演进路线图

```
阶段一：MCP 协议基础
  └─ http-demo          MCP Server 最简实现（HTTP 传输）
  └─ stdio-demo         MCP Server stdio 传输方式

阶段二：MCP 工具扩展
  └─ stdio-filesystem   文件系统操作工具
  └─ stdio-sqlite       数据库查询工具
  └─ stdio-browser      浏览器自动化工具

阶段三：Agent 核心原理
  └─ harness-demo       Harness 运行时支撑层（底层原理）
  └─ simple-agent-demo  最简 Agent 实现（手写 Agentic Loop）

阶段四：Agent 框架应用
  └─ langchain-demo     LangChain 框架构建 Agent
  └─ langgraph-demo     LangGraph 图状态机构建 Agent
  └─ langgraph-multi-agent-demo  多 Agent 协作系统
  └─ agentscope-demo    AgentScope 多 Agent 框架（阿里开源）

阶段五：RAG 知识增强
  └─ rag-demo           检索增强生成（RAG）完整实现
```

---

## 阶段一：MCP 协议基础

### 1. [http-demo](./http-demo/server.py) — MCP Server 最简实现

**技术点：MCP 协议 + Streamable HTTP 传输**

| 项目 | 说明 |
|------|------|
| 核心技术 | MCP（Model Context Protocol）、FastMCP、HTTP |
| 传输方式 | Streamable HTTP（POST 请求 + SSE 响应） |
| 提供工具 | `get_weather(city)`、`list_cities()` |
| 运行方式 | 常驻进程，监听 `http://127.0.0.1:8080/mcp` |

**学到什么：**
- MCP 协议的基本结构（JSON-RPC 2.0）
- 如何用 `FastMCP` 快速定义一个 MCP Server
- MCP 工具的注册方式（`@mcp.tool()` 装饰器）
- 如何接入 Knot CLI / Claude Desktop

**参考链接：**
- [FastMCP 文档](https://github.com/jlowin/fastmcp)
- [MCP 官方协议规范](https://modelcontextprotocol.io/specification)

---

### 2. [stdio-demo](./stdio-demo/server.py) — stdio 传输方式

**技术点：MCP stdio 传输 + 子进程通信**

| 项目 | 说明 |
|------|------|
| 核心技术 | MCP stdio 传输、JSON-RPC、stdin/stdout |
| 传输方式 | stdin 读请求 / stdout 写响应 / stderr 写日志 |
| 提供工具 | `add`、`subtract`、`multiply`、`divide`、`power` |
| 运行方式 | 由 MCP Client 作为子进程启动 |

**学到什么：**
- stdio 与 HTTP 两种传输方式的本质区别
- 为什么本地工具用 stdio、远程服务用 HTTP
- MCP 协议的完整握手流程（initialize → tools/list → tools/call）

**HTTP vs stdio 对比：**

| 特性 | HTTP（http-demo） | stdio（stdio-demo） |
|------|-------------------|---------------------|
| 是否需要端口 | ✅ 需要 | ❌ 不需要 |
| 启动方式 | Server 常驻 | Client 启动子进程 |
| 适用场景 | 远程服务、跨网络 | 本地工具、CLI 集成 |
| 并发能力 | 支持并发 | 单进程串行 |

---

## 阶段二：MCP 工具扩展

### 3. [stdio-filesystem](./stdio-filesystem/server.py) — 文件系统工具

**技术点：MCP 工具 + 安全沙箱**

提供工具：`list_dir`、`read_file`、`write_file`、`search_files`、`get_info`

**学到什么：**
- 如何实现有安全限制的 MCP 工具（白名单目录 `ALLOWED_DIRS`）
- 真实工具的参数校验和错误处理模式

---

### 4. [stdio-sqlite](./stdio-sqlite/server.py) — 数据库查询工具

**技术点：MCP 工具 + 只读数据库访问**

提供工具：`list_tables`、`describe_table`、`query_data`、`get_table_stats`

**学到什么：**
- 如何把数据库能力封装成 MCP 工具
- 只读安全策略（禁止 DROP/DELETE/UPDATE 等危险操作）
- LLM 通过自然语言查询数据库的完整链路

---

### 5. [stdio-browser](./stdio-browser/server.py) — 浏览器自动化工具

**技术点：MCP 工具 + Playwright 浏览器自动化**

提供工具：`browse_url`、`get_page_content`、`screenshot`、`click_element`、`fill_input`、`execute_javascript`

**学到什么：**
- 如何把 Playwright 封装成 MCP 工具
- LLM 驱动浏览器完成自动化任务的模式

**参考链接：**
- [Playwright Python 文档](https://playwright.dev/python/)

---

## 阶段三：Agent 核心原理

> 这两个 Demo 是理解 Agent 工作原理的关键，建议仔细阅读代码。

### 6. [harness-demo](./harness-demo/harness.py) — Harness 运行时支撑层

**技术点：Agent 底层架构 + Harness 模式**

```
Harness = 模型的运行时支撑层
        = 把"会生成文本的模型"变成"能在真实世界里可靠完成任务的系统"
```

| Harness 职责 | 实现方式 |
|--------------|---------|
| 调用循环（Agentic Loop） | `agent_loop()` 函数 |
| 工具路由与执行 | `execute_tool()` 函数 |
| 上下文/记忆管理 | `conversation_history` 列表 |
| 权限与沙箱 | `ALLOWED_DIRS` + `check_path_allowed()` |
| 验证与兜底 | `validate_tool_call()` 函数 |
| 观测与审计 | `log_step()` 函数（记录 token 消耗） |

**学到什么：**
- Agent 的完整运行时架构
- 为什么需要 Harness（模型只负责"吃 token 吐 token"，其余都是 Harness 的事）

**参考链接：**
- [Building Effective Agents（Anthropic 官方指南）](https://www.anthropic.com/research/building-effective-agents)

---

### 7. [simple-agent-demo](./simple-agent-demo/agent.py) — 最简 Agent 实现

**技术点：手写 Agentic Loop + Function Calling**

```python
# 核心循环（约 20 行代码）
while round_count < max_rounds:
    response = call_llm(user_input)       # 1. 调用 LLM
    if not response["tool_calls"]:
        return response["content"]         # 4. 无工具调用 → 返回答案
    for tool_call in response["tool_calls"]:
        result = execute_tool(tool_call)   # 2. 执行工具
        add_to_history(result)             # 3. 结果加入上下文
```

**学到什么：**
- Function Calling 的完整流程（LLM 声明调用 → 应用执行 → 结果回传）
- Agentic Loop 的本质：循环调用 LLM，直到不再需要工具
- 对话历史（`conversation_history`）如何维护上下文

---

## 阶段四：Agent 框架应用

> 在理解了底层原理后，学习框架就是学习"框架帮你封装了哪些底层细节"。

### 8. [langchain-demo](./langchain-demo/agent.py) — LangChain 框架

**技术点：LangChain 1.x + `create_agent` API**

```python
# LangChain 的核心用法（3 行创建 Agent）
llm = ChatOpenAI(model="gpt-4o-mini")
agent = create_agent(model=llm, tools=tools)
result = agent.invoke({"messages": [("human", "查询北京天气")]})
```

**学到什么：**
- `@tool` 装饰器定义工具
- `create_agent` 返回的是一个 `CompiledStateGraph`（底层是 LangGraph）
- LangChain 1.x 与旧版（0.x）的区别

**参考链接：**
- [LangChain 官方文档](https://python.langchain.com/)
- [LangChain Agents 文档](https://docs.langchain.com/oss/python/langchain/agents)

---

### 9. [langgraph-demo](./langgraph-demo/agent.py) — LangGraph 图状态机

**技术点：StateGraph + Node + Edge + 条件路由**

```
用户输入
  ↓
START → [agent 节点] → 有工具调用？
                          ↓ 是
                       [tools 节点] → [agent 节点] → ...
                          ↓ 否
                         END
```

**核心概念：**

| 概念 | 作用 | 代码 |
|------|------|------|
| `AgentState` | 定义图的状态（消息列表） | `TypedDict` |
| Node（节点） | 每个处理步骤 | `add_node()` |
| Edge（边） | 节点间的流转 | `add_edge()` |
| 条件边 | 根据状态决定下一步 | `add_conditional_edges()` |
| `workflow.compile()` | 编译图为可执行 Agent | — |

**学到什么：**
- 为什么需要图结构（天然支持循环、条件分支、并行）
- `tools_condition` 如何判断是否需要调用工具
- 如何可视化 Agent 的执行流程（`app.get_graph().draw_png()`）

**参考链接：**
- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)

---

### 10. [langgraph-multi-agent-demo](./langgraph-multi-agent-demo/agent.py) — 多 Agent 协作

**技术点：多 Agent 串联 + Supervisor 路由模式**

```
用户输入
  ↓
[Supervisor 节点]  ← 总调度，决定交给哪个 Agent
  ↓
[Weather Agent]    ← 专门处理天气查询
  ↓
[Calculator Agent] ← 专门处理数学计算
  ↓
[Supervisor 节点]  ← 判断是否全部完成
  ↓
END
```

**学到什么：**
- 多 Agent 的本质：每个 Agent 是图中的一个节点，有自己的工具集
- Supervisor 模式：用一个"总调度"节点决定任务分发
- 多 Agent 之间是**串行**的（通过共享 State 传递信息）

**参考链接：**
- [LangGraph Multi-Agent 文档](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [详细学习文档](./langgraph-multi-agent-demo/LEARN.md)

---

### 11. [agentscope-demo](./agentscope-demo/agent.py) — AgentScope 多 Agent 框架

**技术点：AgentScope + Pipeline 编排 + ReAct Agent**

```
AgentScope 核心设计：
  消息驱动（Msg）+ Pipeline 编排 + 内置 Agent 类型

编排方式：
  sequentialpipeline  → 顺序执行（A → B → C）
  ifelsepipeline      → 条件分支（if 条件 then A else B）
  whilelooppipeline   → 循环执行
  parallelpipeline    → 并行执行
```

| 概念 | 说明 | 类比 |
|------|------|------|
| `Msg` | Agent 间通信的消息对象 | LangGraph 的 State |
| `DialogAgent` | 基本对话 Agent | LangChain 的 ChatModel |
| `ReActAgent` | 带工具的推理 Agent | LangGraph 的 agent+tools 循环 |
| `Pipeline` | Agent 编排方式 | LangGraph 的 Graph |
| `ServiceToolkit` | 工具注册管理 | MCP 的 @tool 装饰器 |

**四个 Demo 场景：**

| Demo | 内容 | 验证点 |
|------|------|--------|
| Demo 1 | 基本对话 Agent | 最简 Agent 创建与消息交互 |
| Demo 2 | ReAct Agent | 工具调用 + 思考-行动-观察循环 |
| Demo 3 | 多 Agent Pipeline | 翻译→润色→审核 流水线协作 |
| Demo 4 | 条件分支 Pipeline | 根据问题类型路由到不同 Agent |

**学到什么：**
- AgentScope 的消息驱动设计（一切通信基于 `Msg` 对象）
- Pipeline 编排比 Graph 更直观（Python 函数式风格）
- `ReActAgent` 内置了完整的 Agentic Loop（无需手写）
- 与 LangGraph 的核心区别：Pipeline 函数式 vs Graph 图结构

**AgentScope vs LangGraph 对比：**

| 特性 | AgentScope | LangGraph |
|------|-----------|-----------|
| 编排方式 | Pipeline 函数式 | Graph 图结构 |
| 学习曲线 | 较低（Python 函数风格） | 中等（需理解图概念） |
| 多 Agent 通信 | 消息传递（Msg） | 共享状态（State） |
| 条件路由 | `ifelsepipeline` | `conditional_edges` |
| 并行执行 | `parallelpipeline` | `Send()` API |
| 分布式 | 原生支持 | 需额外配置 |
| 生态 | 阿里系 | LangChain 生态 |

**参考链接：**
- [AgentScope GitHub](https://github.com/modelscope/agentscope)
- [AgentScope 官方文档](https://modelscope.github.io/agentscope/)
- [AgentScope 论文](https://arxiv.org/abs/2402.14034)

---

## 阶段五：RAG 知识增强

### 12. [rag-demo](./rag-demo/rag.py) — 检索增强生成

**技术点：Embedding + 向量数据库 + RAG 链**

```
【构建阶段（一次性）】
文档 → OpenAI Embedding → 向量 → Chroma 向量库

【查询阶段（每次问答）】
用户问题 → 向量检索（top_k=3）→ 相关文档
                                      ↓
                          文档 + 问题 → LLM → 回答
```

**三个测试场景：**

| 场景 | 问题类型 | 验证点 |
|------|---------|--------|
| Test 1 | 文档中有直接答案 | 准确检索并回答 |
| Test 2 | 需要综合多篇文档 | 跨文档语义检索 |
| Test 3 | 文档中没有答案 | 不编造，说"没有相关信息" |

**学到什么：**
- Embedding 的本质：把文本转成向量，语义相似的文本向量距离更近
- 向量检索 vs 关键词检索的区别
- RAG 为什么能解决 LLM 知识截止日期和私有文档的问题
- `prompt | llm` 链式调用（LangChain Expression Language）

**参考链接：**
- [LangChain RAG 文档](https://python.langchain.com/docs/tutorials/rag/)
- [Chroma 向量数据库](https://docs.trychroma.com/)
- [OpenAI Embeddings 文档](https://platform.openai.com/docs/guides/embeddings)

---

## 技术点全景总结

| 技术点 | 覆盖的 Demo | 重要程度 |
|--------|------------|---------|
| MCP 协议（JSON-RPC） | http-demo, stdio-demo | ⭐⭐⭐⭐⭐ |
| HTTP vs stdio 传输 | http-demo, stdio-demo | ⭐⭐⭐⭐ |
| MCP 工具开发 | stdio-filesystem, stdio-sqlite, stdio-browser | ⭐⭐⭐⭐⭐ |
| Function Calling | simple-agent-demo, harness-demo | ⭐⭐⭐⭐⭐ |
| Agentic Loop | simple-agent-demo, harness-demo | ⭐⭐⭐⭐⭐ |
| 上下文/记忆管理 | simple-agent-demo, harness-demo | ⭐⭐⭐⭐ |
| 权限控制与沙箱 | harness-demo, stdio-filesystem | ⭐⭐⭐ |
| LangChain 框架 | langchain-demo | ⭐⭐⭐⭐ |
| LangGraph 图状态机 | langgraph-demo, langgraph-multi-agent-demo | ⭐⭐⭐⭐⭐ |
| 多 Agent 协作 | langgraph-multi-agent-demo, agentscope-demo | ⭐⭐⭐⭐ |
| Pipeline 编排 | agentscope-demo | ⭐⭐⭐⭐ |
| Embedding 向量化 | rag-demo | ⭐⭐⭐⭐⭐ |
| 向量数据库（Chroma） | rag-demo | ⭐⭐⭐⭐ |
| RAG 检索增强生成 | rag-demo | ⭐⭐⭐⭐⭐ |

---

## 各 Demo 对比速查

| Demo | 核心框架 | 代码量 | 难度 | 适合人群 |
|------|---------|--------|------|---------|
| http-demo | FastMCP | ~100 行 | ⭐ | 入门 |
| stdio-demo | FastMCP | ~150 行 | ⭐ | 入门 |
| stdio-filesystem | FastMCP | ~200 行 | ⭐⭐ | 初级 |
| stdio-sqlite | FastMCP | ~150 行 | ⭐⭐ | 初级 |
| stdio-browser | FastMCP + Playwright | ~200 行 | ⭐⭐⭐ | 中级 |
| harness-demo | 纯 OpenAI SDK | ~500 行 | ⭐⭐⭐ | 中级 |
| simple-agent-demo | 纯 OpenAI SDK | ~200 行 | ⭐⭐ | 初级 |
| langchain-demo | LangChain 1.x | ~200 行 | ⭐⭐ | 初级 |
| langgraph-demo | LangGraph | ~250 行 | ⭐⭐⭐ | 中级 |
| langgraph-multi-agent-demo | LangGraph | ~450 行 | ⭐⭐⭐⭐ | 进阶 |
| agentscope-demo | AgentScope | ~300 行 | ⭐⭐⭐ | 中级 |
| rag-demo | LangChain + Chroma | ~200 行 | ⭐⭐⭐ | 中级 |

---

## 推荐学习路径

### 路径 A：快速上手 MCP 开发（1-2天）
```
http-demo → stdio-demo → stdio-filesystem → stdio-sqlite
```

### 路径 B：深入理解 Agent 原理（2-3天）
```
simple-agent-demo → harness-demo → langchain-demo → langgraph-demo
```

### 路径 C：完整 AI 应用开发（1周）
```
http-demo → stdio-demo → simple-agent-demo → langchain-demo
→ langgraph-demo → langgraph-multi-agent-demo → agentscope-demo → rag-demo
```

---

*最后更新：2026-06-12*

---

## 附录：各 Demo 环境恢复与执行方式

> 所有 venv 虚拟环境已删除以节省空间，每次运行前需先恢复依赖。
> 通用步骤如下：
>
> ```bash
> cd <项目目录>
> python3 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> ```

---

### http-demo

```bash
cd http-demo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 启动 MCP Server（常驻进程）
python server.py
```

---

### stdio-demo

```bash
cd stdio-demo
# stdio-demo 无 venv，直接用系统 Python 或手动安装 mcp
python server.py          # 由 MCP Client 启动，也可直接运行测试
python test_stdio.py      # 运行测试脚本
```

---

### stdio-filesystem

```bash
cd stdio-filesystem
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

---

### stdio-sqlite

```bash
cd stdio-sqlite
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py
```

---

### stdio-browser

```bash
cd stdio-browser
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# 首次运行需安装 Playwright 浏览器
playwright install chromium
python server.py
```

---

### harness-demo

```bash
cd harness-demo
# harness-demo 无独立 venv，需手动安装依赖
pip install openai python-dotenv
python harness.py         # 运行主 Agent
python test_harness.py    # 运行测试
```

---

### simple-agent-demo

```bash
cd simple-agent-demo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python agent.py
```

---

### langchain-demo

```bash
cd langchain-demo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python agent.py
```

---

### langgraph-demo

```bash
cd langgraph-demo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python agent.py
```

---

### langgraph-multi-agent-demo

```bash
cd langgraph-multi-agent-demo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python agent.py
```

---

### rag-demo

```bash
cd rag-demo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python rag.py
```

---

### agentscope-demo

```bash
cd agentscope-demo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python agent.py
```

---

> **提示：** 所有 demo 均需在项目根目录下创建 `.env` 文件，配置 OpenAI API Key：
>
> ```bash
> OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
> # 如使用代理或第三方兼容接口，还需配置：
> OPENAI_BASE_URL=https://your-proxy-url/v1
> ```
