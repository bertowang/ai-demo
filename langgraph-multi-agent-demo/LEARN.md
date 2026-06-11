# LangGraph Multi-Agent Demo 学习文档

> 目标读者：Python 初学者 / AI Agent 入门者
> 对应文件：`agent.py`

---

## 一、这个 Demo 是干什么的？

这个 Demo 模拟了一个"多智能体协作"的场景：

- 有两个专门的 AI Agent（智能体）：
  - **天气 Agent**：负责查询城市天气
  - **计算 Agent**：负责做数学计算
- 它们按照固定顺序工作：先天气，再计算
- 用户只需提一个问题，系统自动决定调用哪个 Agent

**举例：**
- 问"北京天气怎么样？" → 只调用天气 Agent
- 问"计算 15 * 37" → 先经过天气 Agent（不调用工具），再调用计算 Agent
- 问"北京温度多少？如果 >20 就算 100/3" → 天气 Agent 查天气，计算 Agent 做计算

---

## 二、核心概念速览

| 概念 | 通俗理解 |
|---|---|
| **LangGraph** | 一个把 AI 调用流程画成"流程图"的框架 |
| **Node（节点）** | 流程图中的一个步骤，比如"调用天气 Agent" |
| **Edge（边）** | 节点之间的连线，决定下一步去哪 |
| **State（状态）** | 整个流程共享的"黑板"，记录消息历史和完成情况 |
| **Tool（工具）** | AI 可以调用的函数，比如查天气、做计算 |
| **ToolNode** | LangGraph 内置节点，专门负责执行 Tool 调用 |

---

## 三、整体流程图

```
用户输入
   ↓
[weather_agent] ← 天气 Agent（LLM 决策）
   ↓
需要查天气？
  ├── 是 → [weather_tools] 执行工具 → 回到 [weather_agent]
  └── 否 → [weather_done] 标记天气完成
                ↓
         需要计算？
           ├── 是 → [calculator_agent] ← 计算 Agent（LLM 决策）
           │            ↓
           │        需要计算？
           │          ├── 是 → [calculator_tools] 执行工具 → 回到 [calculator_agent]
           │          └── 否 → [calculator_done] 标记计算完成 → 结束
           └── 否 → 结束
```

---

## 四、代码逐段解析

### 4.1 配置部分

```python
API_KEY: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
BASE_URL: str = "http://v2.open.venus.oa.com/llmproxy"
MODEL: str = "gpt-4o-mini"
```

这里配置了 LLM 的连接信息：API 密钥、接口地址、使用的模型名称。

---

### 4.2 工具函数（Tools）

```python
def get_weather(city: str) -> str:
    weather_data = {
        "Beijing": "Sunny, 25C",
        "Shanghai": "Cloudy, 28C",
        ...
    }
    return weather_data.get(city, f"Unknown city: {city}")

def calculate(expression: str) -> str:
    result = eval(expression)
    return f"Result: {expression} = {result}"
```

这是两个**普通 Python 函数**，模拟真实的天气查询和数学计算。

> ⚠️ 注意：这里的天气数据是写死的假数据，真实项目中应该调用真实 API。

---

### 4.3 状态定义（State）

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    weather_done: bool   # 天气 Agent 是否完成
    calc_done: bool      # 计算 Agent 是否完成
```

**State 是整个流程的"共享黑板"**，所有节点都能读写它。

- `messages`：对话历史（用户消息、AI 回复、工具结果都存在这里）
- `weather_done`：布尔值，标记天气任务是否完成
- `calc_done`：布尔值，标记计算任务是否完成

`add_messages` 是 LangGraph 提供的特殊注解，表示每次更新 `messages` 时是**追加**而不是覆盖。

---

### 4.4 创建天气 Agent 节点

```python
def create_weather_node():
    llm = create_llm(0.3)          # 创建 LLM，temperature=0.3（较稳定）

    @tool
    def weather_tool(city: str) -> str:
        """Get weather for a city."""
        return get_weather(city)

    tools = [weather_tool]
    llm_with_tools = llm.bind_tools(tools)  # 把工具"绑定"给 LLM
```

**关键点：`llm.bind_tools(tools)`**

这一步告诉 LLM："你有这些工具可以用"。LLM 在回复时，如果认为需要查天气，就会在回复中包含一个"工具调用请求"（tool_calls），而不是直接回答。

---

#### 4.4.1 天气 Agent 的核心节点函数

```python
def node(state: AgentState) -> Dict[str, Any]:
    messages = state["messages"]

    # 关键逻辑：如果已经有工具结果了，就不要再调用工具了
    has_tool_result = any(isinstance(m, ToolMessage) for m in messages)
    if has_tool_result:
        invoke_messages = list(messages) + [SystemMessage(
            content="You already have the tool results. Please summarize and answer directly without calling any more tools."
        )]
    else:
        invoke_messages = list(messages)

    response = llm_with_tools.invoke(invoke_messages)
    return {"messages": [response], "weather_done": False, ...}
```

**为什么要检测 `has_tool_result`？**

这是一个防止"死循环"的关键设计：

1. 第一次进入节点：LLM 看到用户问题，决定调用 `weather_tool`
2. 工具执行完毕，结果存入 `messages`
3. 第二次进入节点：如果不加限制，LLM 可能**再次**调用工具（因为它觉得还没给出最终回答）
4. 加了检测后：发现已有工具结果，注入一条系统消息，强制 LLM 直接总结回答

---

#### 4.4.2 天气完成标记函数

```python
def after_tools(state: AgentState) -> Dict[str, Any]:
    print("  [Weather Agent] Task completed")
    return {"weather_done": True}   # 把黑板上的 weather_done 设为 True
```

这个函数对应图中的 `weather_done` 节点，只做一件事：把状态里的 `weather_done` 标记为 `True`。

---

### 4.5 创建计算 Agent 节点

结构与天气 Agent 完全相同，区别在于：

```python
# 检测是否已有计算结果（通过 "Result:" 关键字判断）
has_calc_result = any(
    isinstance(m, ToolMessage) and "Result:" in m.content
    for m in messages
)
```

计算 Agent 通过检查 ToolMessage 的内容是否包含 `"Result:"` 来判断是否已经执行过计算。

---

### 4.6 路由函数（决定下一步去哪）

#### route_weather：天气 Agent 执行后的路由

```python
def route_weather(state: AgentState) -> str:
    last_msg = state["messages"][-1]

    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "weather_tools"   # LLM 想调用工具 → 去执行工具
    
    return "weather_done"        # LLM 直接回答了 → 标记完成
```

**判断逻辑：** 看最后一条消息是否包含 `tool_calls`（工具调用请求）。

- 有 `tool_calls` → LLM 想查天气 → 去 `weather_tools` 节点执行
- 没有 `tool_calls` → LLM 直接回答了 → 去 `weather_done` 节点标记完成

---

#### should_continue：天气完成后，是否需要计算？

```python
def should_continue(state: AgentState) -> str:
    # 从消息历史中找到用户的原始问题
    user_request = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            user_request = msg.content.lower()
            break

    # 判断用户是否需要计算
    needs_calc = any(word in user_request for word in
                     ["calculate", "math", "*", "+", "/", "-", "100/3"])

    if state.get("weather_done") and needs_calc and not state.get("calc_done"):
        return "calculator_agent"   # 需要计算 → 去计算 Agent

    return END                      # 不需要计算 → 结束
```

**判断逻辑：** 用关键词匹配用户原始问题，看是否包含计算相关词汇。

> ⚠️ 这是一个简化实现，真实项目中应该让 LLM 来判断是否需要计算，而不是用关键词匹配。

---

### 4.7 构建图（Graph）

```python
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("weather_agent", weather["node"])
workflow.add_node("weather_tools", weather["tools"])
workflow.add_node("weather_done", weather["after_tools"])
workflow.add_node("calculator_agent", calc["node"])
workflow.add_node("calculator_tools", calc["tools"])
workflow.add_node("calculator_done", calc["after_tools"])

# 添加边
workflow.add_edge(START, "weather_agent")              # 入口 → 天气 Agent
workflow.add_edge("weather_tools", "weather_agent")    # 工具执行完 → 回天气 Agent
workflow.add_edge("calculator_tools", "calculator_agent")  # 工具执行完 → 回计算 Agent
workflow.add_edge("calculator_done", END)              # 计算完成 → 结束

# 添加条件边（根据路由函数决定走哪条路）
workflow.add_conditional_edges("weather_agent", route_weather, {...})
workflow.add_conditional_edges("weather_done", should_continue, {...})
workflow.add_conditional_edges("calculator_agent", route_calculator, {...})

app = workflow.compile()   # 编译成可执行的图
```

**节点 vs 条件边：**
- `add_edge`：固定走向，A 执行完一定去 B
- `add_conditional_edges`：动态走向，根据路由函数的返回值决定去哪

---

## 五、三个测试用例的执行轨迹

### Test 1：只查天气

```
输入: "What's the weather in Beijing?"

执行轨迹:
START
  → weather_agent（LLM 决定调用 weather_tool）
  → weather_tools（执行 weather_tool，返回 "Sunny, 25C"）
  → weather_agent（LLM 看到结果，直接总结回答）
  → weather_done（标记 weather_done=True）
  → should_continue（用户没说要计算）
  → END

消息历史:
  1. HumanMessage: "What's the weather in Beijing?"
  2. AIMessage: [tool_calls: weather_tool(city="Beijing")]
  3. ToolMessage: "Sunny, 25C"
  4. AIMessage: "The weather in Beijing is sunny with a temperature of 25°C."
```

---

### Test 2：只做计算

```
输入: "Calculate 15 * 37"

执行轨迹:
START
  → weather_agent（LLM 判断不需要查天气，直接回答）
  → weather_done（标记 weather_done=True）
  → should_continue（用户问题包含 "*"，需要计算）
  → calculator_agent（LLM 决定调用 calc_tool）
  → calculator_tools（执行 calc_tool，返回 "Result: 15 * 37 = 555"）
  → calculator_agent（LLM 看到结果，直接总结回答）
  → calculator_done（标记 calc_done=True）
  → END
```

---

### Test 3：多 Agent 协作

```
输入: "What's Beijing's temperature? If >20, calculate 100/3"

执行轨迹:
START
  → weather_agent（LLM 调用 weather_tool）
  → weather_tools（返回 "Sunny, 25C"）
  → weather_agent（LLM 总结：25°C > 20，需要计算）
  → weather_done（标记 weather_done=True）
  → should_continue（用户问题包含 "100/3"，需要计算）
  → calculator_agent（LLM 调用 calc_tool）
  → calculator_tools（返回 "Result: 100/3 = 33.33..."）
  → calculator_agent（LLM 总结最终答案）
  → calculator_done（标记 calc_done=True）
  → END
```

---

## 六、关键设计模式总结

### 模式 1：工具绑定（Tool Binding）

```python
llm_with_tools = llm.bind_tools(tools)
```

LLM 本身不能执行代码，但通过 `bind_tools` 告诉它"你有这些工具"。LLM 在回复时会在 `tool_calls` 字段里写明要调用哪个工具、传什么参数，然后由 `ToolNode` 实际执行。

### 模式 2：状态驱动路由（State-Driven Routing）

用 `weather_done` 和 `calc_done` 两个布尔值来追踪进度，路由函数根据这些状态决定下一步。这比用复杂的条件判断更清晰。

### 模式 3：防止工具重复调用

```python
has_tool_result = any(isinstance(m, ToolMessage) for m in messages)
if has_tool_result:
    # 注入系统消息，强制 LLM 总结而不是再次调用工具
    invoke_messages += [SystemMessage("Please summarize...")]
```

这是解决 LLM 在 Agent 循环中"停不下来"问题的实用技巧。

### 模式 4：顺序执行（Sequential Execution）

天气 Agent 永远先执行，计算 Agent 永远后执行。这种简单的顺序设计避免了复杂的调度逻辑，也不容易出现递归超限的问题。

---

## 七、与其他 Demo 的对比

| 特性 | simple-agent-demo | langchain-demo | langgraph-multi-agent-demo |
|---|---|---|---|
| 实现方式 | 手写循环 | LangChain AgentExecutor | LangGraph 状态图 |
| 多 Agent | ❌ 单 Agent | ❌ 单 Agent | ✅ 多 Agent |
| 流程可视化 | ❌ | ❌ | ✅ 可导出图 |
| 状态管理 | 手动维护列表 | 框架自动管理 | TypedDict 状态机 |
| 扩展性 | 低 | 中 | 高 |
| 学习难度 | ⭐ 低 | ⭐⭐ 中 | ⭐⭐⭐ 较高 |

---

## 八、常见问题

**Q: 为什么 Test 2（只计算）也要先经过天气 Agent？会不会浪费时间？**

A: 因为图的入口是硬编码的：

```python
workflow.add_edge(START, "weather_agent")  # 永远从天气 Agent 开始
```

没有任何"先判断用户问什么、再决定入口"的逻辑，所有请求都必须从 `weather_agent` 进入。

**会浪费时间**。Test 2 的实际路径是：

```
用户: "Calculate 15 * 37"
  ↓
weather_agent（天气 Agent 的 LLM 被调用一次）← 白白浪费一次 API 调用
  → LLM 判断：这不是天气问题，不调用工具，直接回复
  ↓
weather_done → should_continue → calculator_agent（才真正开始工作）
```

**如何解决？真实项目有两种方案：**

---

#### 方案 1：关键词分发（Router 节点）

在 `START` 后加一个轻量的分发节点，用规则判断用户意图，直接跳到对应 Agent：

```python
def router_node(state: AgentState) -> str:
    """根据用户问题，决定先去哪个 Agent"""
    user_msg = state["messages"][-1].content.lower()
    if any(w in user_msg for w in ["weather", "temperature", "sunny", "rain"]):
        return "weather_agent"
    elif any(w in user_msg for w in ["calculate", "math", "*", "+", "-", "/"]):
        return "calculator_agent"
    return "weather_agent"  # 默认走天气 Agent

# 图的入口改为 router
workflow.add_edge(START, "router")
workflow.add_node("router", lambda state: state)  # router 节点本身不修改状态
workflow.add_conditional_edges(
    "router",
    router_node,
    {
        "weather_agent": "weather_agent",
        "calculator_agent": "calculator_agent",
    }
)
```

执行路径变为：

```
用户: "Calculate 15 * 37"
  ↓
router（关键词匹配，发现有 "*"）
  ↓ 直接跳过天气 Agent！
calculator_agent → calculator_tools → calculator_done → END
```

**优点：** 无额外 LLM 调用，速度快，成本低
**缺点：** 关键词匹配不够智能，遇到"帮我算一下北京今天气温的平方"这类复合问题容易判断错

---

#### 方案 2：Supervisor 模式（LLM 智能分发）

用一个专门的"主管 LLM"来理解用户意图，动态决定调用哪个 Agent，甚至决定调用顺序：

```python
from langchain_core.messages import SystemMessage

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """主管节点：让 LLM 决定下一步派给哪个 Agent"""
    llm = create_llm()
    
    system_prompt = """你是一个任务调度员。根据用户的问题，判断需要调用哪个 Agent：
- weather_agent：处理天气相关问题
- calculator_agent：处理数学计算问题
- FINISH：任务已完成，无需继续

只回复 Agent 名称，不要解释。"""
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *state["messages"]
    ])
    
    next_agent = response.content.strip()
    return {"next": next_agent}  # 把决策存入状态

# 图结构
workflow.add_node("supervisor", supervisor_node)
workflow.add_edge(START, "supervisor")  # 入口是主管
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["next"],  # 根据主管的决策路由
    {
        "weather_agent": "weather_agent",
        "calculator_agent": "calculator_agent",
        "FINISH": END,
    }
)

# 每个 Agent 完成后，回到主管重新决策
workflow.add_edge("weather_done", "supervisor")
workflow.add_edge("calculator_done", "supervisor")
```

执行路径变为：

```
用户: "Calculate 15 * 37"
  ↓
supervisor（LLM 判断：这是计算问题）
  ↓ 直接跳过天气 Agent！
calculator_agent → calculator_tools → calculator_done
  ↓
supervisor（LLM 判断：任务完成）→ FINISH → END
```

**优点：** 智能、灵活，能处理复杂意图，Agent 顺序可动态调整
**缺点：** 每次路由都要调用一次 LLM，增加延迟和成本

---

#### 两种方案对比

| | 方案 1：关键词 Router | 方案 2：Supervisor 模式 |
|---|---|---|
| **额外 LLM 调用** | ❌ 无 | ✅ 每次路由一次 |
| **智能程度** | 低（规则匹配） | 高（LLM 理解意图） |
| **复杂问题处理** | 容易判断错 | 准确 |
| **实现难度** | ⭐ 简单 | ⭐⭐⭐ 较复杂 |
| **适用场景** | 意图明确、分类简单 | 意图模糊、任务复杂 |

> 💡 **真实项目推荐**：如果 Agent 数量 ≤ 3 且意图清晰，用方案 1；Agent 数量多或任务复杂，用方案 2（Supervisor 模式是业界主流的多 Agent 架构）。

---

**本 Demo 为什么不做这个优化？** 刻意简化，降低学习门槛。理解了本 Demo 的串行流程后，再学习加分发节点会更容易。

**Q: `recursion_limit` 是什么？**

A: LangGraph 为了防止无限循环，限制了图的最大执行步数。Test 1/2 设置为 10，Test 3 设置为 30（因为步骤更多）。

**Q: 为什么 `should_continue` 用关键词匹配而不是让 LLM 判断？**

A: 这是简化实现，降低学习门槛。真实项目中，更好的做法是让 LLM 在天气 Agent 的回复中明确说明"需要/不需要计算"，然后路由函数解析这个意图。

---

## 九、如何运行

```bash
# 进入项目目录
cd langgraph-multi-agent-demo

# 使用项目自带的虚拟环境运行（重要！）
./venv/bin/python agent.py

# 或者先激活虚拟环境
source venv/bin/activate
python agent.py
```

> ⚠️ 不要直接用系统的 `python agent.py`，因为系统 Python 没有安装 langchain 等依赖。

---

## 十、多 Agent 体现在哪里？

这是最容易让人困惑的问题：**代码里哪里是"多个 Agent"？**

### 10.1 两个 Agent 的本质区别

"多 Agent" 的核心是：**每个 Agent 有自己独立的 LLM 实例 + 独立的工具集**。

```python
# ✅ Agent 1：天气 Agent
def create_weather_node():
    llm = create_llm(temperature=0.3)       # 独立的 LLM 实例（temperature=0.3，较稳定）
    
    @tool
    def weather_tool(city: str) -> str:     # 只有天气工具
        ...
    
    llm_with_tools = llm.bind_tools([weather_tool])   # 只绑定天气工具


# ✅ Agent 2：计算 Agent
def create_calculator_node():
    llm = create_llm(temperature=0.1)       # 独立的 LLM 实例（temperature=0.1，更精确）
    
    @tool
    def calc_tool(expression: str) -> str:  # 只有计算工具
        ...
    
    llm_with_tools = llm.bind_tools([calc_tool])      # 只绑定计算工具
```

**关键点对比：**

| | 天气 Agent | 计算 Agent |
|---|---|---|
| LLM 实例 | 独立创建，`temperature=0.3` | 独立创建，`temperature=0.1` |
| 工具 | 只有 `weather_tool` | 只有 `calc_tool` |
| 职责 | 只处理天气查询 | 只处理数学计算 |
| 互相感知 | ❌ 不知道对方存在 | ❌ 不知道对方存在 |

> 💡 **通俗理解**：就像公司里的两个部门——天气部门只会查天气，计算部门只会做计算。它们各自有自己的"大脑"（LLM）和"工具箱"，互不干扰。

---

### 10.2 多 Agent 在图中的体现

在 LangGraph 的图结构里，两个 Agent 各自占据独立的节点子图：

```
【天气 Agent 子图】              【计算 Agent 子图】
weather_agent ←──────┐          calculator_agent ←──────┐
     ↓                │               ↓                  │
route_weather         │          route_calculator         │
  ├── 有工具调用 → weather_tools ─┘    ├── 有工具调用 → calculator_tools ─┘
  └── 无工具调用 → weather_done        └── 无工具调用 → calculator_done
```

每个 Agent 都有自己的：
- **决策节点**（`weather_agent` / `calculator_agent`）：LLM 思考
- **工具节点**（`weather_tools` / `calculator_tools`）：执行工具
- **完成节点**（`weather_done` / `calculator_done`）：标记完成
- **路由函数**（`route_weather` / `route_calculator`）：决定下一步

---

### 10.3 多 Agent 的协作方式

这个 Demo 采用的是**顺序协作**模式：

```
用户问题
   ↓
天气 Agent 先处理（不管用户问什么，都先过一遍）
   ↓
should_continue 判断：用户需要计算吗？
   ├── 需要 → 计算 Agent 接着处理
   └── 不需要 → 直接结束
```

**Test 3 的协作过程（最能体现多 Agent）：**

```
用户: "北京温度多少？如果 >20 就算 100/3"

Step 1: 天气 Agent 工作
  - 天气 Agent 的 LLM 收到问题
  - 决定调用 weather_tool 查北京天气
  - 得到结果：Sunny, 25C
  - 总结：25°C > 20，需要计算

Step 2: 交接给计算 Agent
  - should_continue 检测到用户问题含 "100/3"
  - 把整个消息历史（含天气结果）传给计算 Agent

Step 3: 计算 Agent 工作
  - 计算 Agent 的 LLM 读取消息历史（包括天气 Agent 的结论）
  - 决定调用 calc_tool 计算 100/3
  - 得到结果：33.33...
  - 给出最终答案
```

> 💡 **关键**：两个 Agent 通过**共享的 `messages` 消息历史**来传递信息。计算 Agent 能"看到"天气 Agent 的工作结果，但它们的 LLM 实例是完全独立的。

---

## 十一、与 langgraph-demo 的区别

### 11.1 架构对比图

**langgraph-demo（单 Agent）：**

```
START → [agent] → [tools] → [agent] → END
           ↑___________|
           （循环直到不再调用工具）
```

**langgraph-multi-agent-demo（多 Agent）：**

```
START → [weather_agent] ⇄ [weather_tools]
              ↓
        [weather_done]
              ↓
        should_continue?
              ↓
       [calculator_agent] ⇄ [calculator_tools]
              ↓
        [calculator_done] → END
```

---

### 11.2 代码层面的核心差异

| 对比维度 | langgraph-demo（单 Agent） | langgraph-multi-agent-demo（多 Agent） |
|---|---|---|
| **LLM 实例数量** | 1 个 | 2 个（各自独立） |
| **工具绑定** | 所有工具绑定到同一个 LLM | 每个 Agent 只绑定自己的工具 |
| **节点数量** | 2 个（agent + tools） | 6 个（每个 Agent 3 个节点） |
| **状态字段** | 只有 `messages` | `messages` + `weather_done` + `calc_done` |
| **路由逻辑** | 用内置的 `tools_condition` | 自定义 `route_weather` / `route_calculator` / `should_continue` |
| **执行模式** | 单循环（一个 Agent 反复调用工具） | 顺序流水线（Agent 1 完成后交给 Agent 2） |

---

### 11.3 关键代码对比

**langgraph-demo：一个 LLM 绑定所有工具**

```python
# 单 Agent：所有工具都给同一个 LLM
tools = [get_weather_tool, calculate_tool]   # 天气 + 计算工具都在一起
llm_with_tools = llm.bind_tools(tools)       # 一个 LLM 包揽所有

# 图结构极简
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.add_conditional_edges("agent", tools_condition)  # 内置路由
workflow.add_edge("tools", "agent")
```

**langgraph-multi-agent-demo：每个 Agent 独立**

```python
# 多 Agent：各自独立
def create_weather_node():
    llm = create_llm(temperature=0.3)
    llm_with_tools = llm.bind_tools([weather_tool])   # 只绑定天气工具

def create_calculator_node():
    llm = create_llm(temperature=0.1)
    llm_with_tools = llm.bind_tools([calc_tool])      # 只绑定计算工具

# 图结构更复杂，有 6 个节点
workflow.add_node("weather_agent", weather["node"])
workflow.add_node("weather_tools", weather["tools"])
workflow.add_node("weather_done", weather["after_tools"])
workflow.add_node("calculator_agent", calc["node"])
workflow.add_node("calculator_tools", calc["tools"])
workflow.add_node("calculator_done", calc["after_tools"])
```

---

### 11.4 什么时候用单 Agent，什么时候用多 Agent？

| 场景 | 推荐方案 | 原因 |
|---|---|---|
| 工具数量少（≤5个），任务单一 | **单 Agent**（langgraph-demo） | 简单直接，不需要协调开销 |
| 工具数量多，容易混淆 | **多 Agent** | 每个 Agent 专注自己领域，减少 LLM 选错工具的概率 |
| 任务有明确的先后依赖 | **多 Agent 顺序模式** | 如本 Demo：先查天气，再根据结果决定是否计算 |
| 任务可以并行 | **多 Agent 并行模式** | 同时查多个城市天气（本 Demo 未实现） |
| 需要一个"总指挥"协调 | **Supervisor 模式** | 更复杂的多 Agent 架构（本 Demo 简化掉了） |

---

### 11.5 一句话总结

> **langgraph-demo** = 一个全能员工，什么工具都会用，自己决定用哪个
>
> **langgraph-multi-agent-demo** = 两个专业员工，各司其职，按流水线协作

---

## 十二、串行 vs 并行：多 Agent 之间的执行顺序

### 12.1 本 Demo 是串行的

**是的，本 Demo 中两个 Agent 是完全串行执行的。**

执行顺序是固定的流水线：

```
天气 Agent 完全执行完毕
        ↓
计算 Agent 才开始执行
```

从图的边定义就能看出来：

```python
# 固定入口：永远从天气 Agent 开始
workflow.add_edge(START, "weather_agent")

# 天气完成后，才可能去计算 Agent
workflow.add_conditional_edges(
    "weather_done",          # 天气 Agent 完成节点
    should_continue,         # 判断是否需要计算
    {
        "calculator_agent": "calculator_agent",   # 需要 → 去计算 Agent
        END: END,                                  # 不需要 → 直接结束
    }
)
```

**没有任何地方让两个 Agent 同时运行**，计算 Agent 必须等天气 Agent 全部跑完才能启动。

---

### 12.2 串行的执行时序图

```
时间轴 ──────────────────────────────────────────────────────→

天气Agent:  [LLM思考] → [调用工具] → [LLM总结] → [标记完成]
                                                        ↓
计算Agent:                                         [LLM思考] → [调用工具] → [LLM总结] → [标记完成]
```

两个 Agent 在时间轴上**不重叠**，严格先后执行。

---

### 12.3 为什么选择串行？

本 Demo 选择串行有两个原因：

**原因 1：任务有依赖关系（Test 3 的场景）**

```
用户: "北京温度多少？如果 >20 就算 100/3"

天气 Agent 必须先跑，得到 "25°C"
         ↓
计算 Agent 才能知道 "25 > 20，需要计算"
```

计算 Agent 的输入依赖天气 Agent 的输出，**有依赖就必须串行**。

**原因 2：简化实现，避免复杂度**

并行需要处理"等待所有 Agent 完成"、"合并结果"等复杂逻辑，串行更容易理解和调试。

---

### 12.4 并行是什么样的？（对比理解）

如果要实现**并行**，比如"同时查北京和上海的天气"，代码结构会完全不同：

```python
# 并行的概念示意（本 Demo 未实现）

# 需要用 Send API 或 fanout 模式
from langgraph.constants import Send

def fanout_node(state):
    # 同时向多个 Agent 发送任务
    return [
        Send("weather_agent_beijing", {"city": "Beijing"}),
        Send("weather_agent_shanghai", {"city": "Shanghai"}),
    ]

# 两个 Agent 会同时执行，互不等待
```

并行的时序图：

```
时间轴 ──────────────────────────────────────────────────────→

北京天气Agent:  [LLM思考] → [调用工具] → [LLM总结]
                                                    ↓ 等两个都完成
上海天气Agent:  [LLM思考] → [调用工具] → [LLM总结]
                                                    ↓
                                              [合并结果节点]
```

---

### 12.5 串行 vs 并行对比总结

| 维度 | 串行（本 Demo） | 并行（未实现） |
|---|---|---|
| **执行方式** | Agent 1 完成 → Agent 2 开始 | Agent 1 和 Agent 2 同时运行 |
| **适用场景** | 任务有依赖（B 需要 A 的结果） | 任务独立（互不依赖） |
| **实现难度** | ⭐ 简单 | ⭐⭐⭐ 复杂（需处理同步、合并） |
| **执行速度** | 慢（总时间 = A时间 + B时间） | 快（总时间 ≈ max(A时间, B时间)） |
| **LangGraph 实现** | `add_edge` + `add_conditional_edges` | `Send` API / fanout 模式 |
| **本 Demo 是否使用** | ✅ 是 | ❌ 否 |

---

### 12.6 一句话总结

> 本 Demo 的多 Agent 是**串行**的：天气 Agent 跑完，计算 Agent 才开始。
> 这是因为任务之间有依赖关系，且串行更简单易懂。
> **并行**适合任务互相独立的场景，需要用 LangGraph 的 `Send` API 实现，复杂度更高。

---

## 十三、Node 和 Edge 的函数抽象

### 13.1 核心结论

> **LangGraph 图里的每个对象，本质上都对应一个 Python 函数。**

| 图对象 | 对应函数 | 函数签名 | 返回值含义 |
|---|---|---|---|
| **Node（节点）** | 状态处理函数 | `(state) -> dict` | 返回要更新的状态字段 |
| **普通 Edge（固定边）** | 无需函数 | — | 固定走向，A 完成必去 B |
| **Conditional Edge（条件边）** | 路由函数 | `(state) -> str` | 返回下一个节点的**名字** |

---

### 13.2 Node = 一个处理状态的函数

每个节点就是一个函数，**输入是当前状态，输出是状态的更新部分**：

```python
# Node 函数的通用模式
def 节点名(state: AgentState) -> Dict[str, Any]:
    # 1. 从 state 读取需要的信息
    messages = state["messages"]
    
    # 2. 做这个节点该做的事（调用 LLM、执行工具、标记状态...）
    response = llm.invoke(messages)
    
    # 3. 返回要更新的字段（不需要返回整个 state，只返回变化的部分）
    return {"messages": [response]}
```

本 Demo 中所有节点函数一览：

```python
# ① 天气 Agent 节点：调用 LLM 决策
def node(state: AgentState) -> Dict:
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "weather_done": False}

# ② 天气完成节点：只更新一个布尔值
def after_tools(state: AgentState) -> Dict:
    return {"weather_done": True}

# ③ 计算 Agent 节点：调用 LLM 决策
def node(state: AgentState) -> Dict:
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "calc_done": False}

# ④ 计算完成节点：只更新一个布尔值
def after_tools(state: AgentState) -> Dict:
    return {"calc_done": True}

# ⑤ ToolNode（内置节点）：执行工具调用，自动把结果追加到 messages
#    本质上也是一个函数，只是 LangGraph 帮你写好了
weather["tools"] = ToolNode([weather_tool])
```

---

### 13.3 Conditional Edge = 一个返回字符串的函数

条件边对应的路由函数，**输入是当前状态，输出是下一个节点的名字（字符串）**：

```python
# Conditional Edge 函数的通用模式
def 路由函数名(state: AgentState) -> str:
    # 读取状态，做判断
    last_msg = state["messages"][-1]
    
    if 条件A:
        return "节点名A"   # 返回字符串，LangGraph 据此跳转
    elif 条件B:
        return "节点名B"
    else:
        return END         # END 是特殊常量，表示结束
```

本 Demo 中所有路由函数一览：

```python
# ① route_weather：天气 Agent 执行后，去工具还是去完成？
def route_weather(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "weather_tools"   # 有工具调用 → 去执行工具
    return "weather_done"        # 没有 → 标记完成

# ② should_continue：天气完成后，去计算还是结束？
def should_continue(state: AgentState) -> str:
    needs_calc = ...             # 判断用户是否需要计算
    if needs_calc:
        return "calculator_agent"
    return END                   # 特殊值，表示图执行结束

# ③ route_calculator：计算 Agent 执行后，去工具还是去完成？
def route_calculator(state: AgentState) -> str:
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "calculator_tools"
    return "calculator_done"
```

---

### 13.4 注册到图：函数 → 图对象

写好函数之后，通过 `add_node` 和 `add_conditional_edges` 把函数"注册"到图里：

```python
workflow = StateGraph(AgentState)

# 注册 Node：给函数起个名字
workflow.add_node("weather_agent",    weather["node"])       # 函数 → 节点
workflow.add_node("weather_tools",    weather["tools"])      # ToolNode → 节点
workflow.add_node("weather_done",     weather["after_tools"])# 函数 → 节点
workflow.add_node("calculator_agent", calc["node"])
workflow.add_node("calculator_tools", calc["tools"])
workflow.add_node("calculator_done",  calc["after_tools"])

# 注册固定 Edge：不需要函数，直接写名字
workflow.add_edge(START, "weather_agent")           # 入口固定去天气 Agent
workflow.add_edge("weather_tools", "weather_agent") # 工具执行完固定回天气 Agent

# 注册 Conditional Edge：传入路由函数
workflow.add_conditional_edges(
    "weather_agent",   # 从哪个节点出发
    route_weather,     # 路由函数（决定去哪）
    {
        "weather_tools": "weather_tools",   # 函数返回 "weather_tools" → 跳到该节点
        "weather_done":  "weather_done",    # 函数返回 "weather_done"  → 跳到该节点
    }
)
```

---

### 13.5 完整的"函数地图"

把本 Demo 所有函数和图对象的对应关系整理如下：

```
图对象名称              对应的函数                    函数作用
─────────────────────────────────────────────────────────────────
[节点] weather_agent    node(state) -> dict           天气 LLM 决策
[节点] weather_tools    ToolNode([weather_tool])      执行天气工具（内置）
[节点] weather_done     after_tools(state) -> dict    标记 weather_done=True
[节点] calculator_agent node(state) -> dict           计算 LLM 决策
[节点] calculator_tools ToolNode([calc_tool])         执行计算工具（内置）
[节点] calculator_done  after_tools(state) -> dict    标记 calc_done=True

[条件边] weather_agent出口    route_weather(state) -> str     返回 "weather_tools" 或 "weather_done"
[条件边] weather_done出口     should_continue(state) -> str   返回 "calculator_agent" 或 END
[条件边] calculator_agent出口 route_calculator(state) -> str  返回 "calculator_tools" 或 "calculator_done"

[固定边] START → weather_agent          （无函数，固定连线）
[固定边] weather_tools → weather_agent  （无函数，固定连线）
[固定边] calculator_tools → calculator_agent （无函数，固定连线）
[固定边] calculator_done → END          （无函数，固定连线）
```

---

### 13.6 一句话总结

> **Node = 处理状态的函数**（输入 state，输出更新的 dict）
> **Conditional Edge = 路由函数**（输入 state，输出下一节点的名字字符串）
> **普通 Edge = 不需要函数**，只是两个节点名之间的固定连线
>
> 整个 LangGraph 图，本质上就是：**一堆函数 + 函数之间的跳转规则**。
