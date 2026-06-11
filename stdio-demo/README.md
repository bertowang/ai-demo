# MCP stdio Demo - 计算器服务

## 简介

这是一个使用 **stdio 传输方式** 的 MCP Server Demo。

与 HTTP 版不同，stdio 版：
- 不监听任何端口
- 通过 **stdin** 读取 JSON-RPC 请求
- 通过 **stdout** 输出 JSON-RPC 响应
- 通过 **stderr** 输出日志（不影响协议通信）
- 由 **MCP Client 作为子进程启动**（如 knot-cli、Claude Desktop）

## 提供的工具

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `add` | 两数相加 | a: number, b: number |
| `subtract` | 两数相减 (a - b) | a: number, b: number |
| `multiply` | 两数相乘 | a: number, b: number |
| `divide` | 两数相除 (a / b) | a: number, b: number |
| `power` | 幂运算 (a 的 b 次方) | a: number, b: number |

## 目录结构

```
/Users/berton/prj/mcp-demo-all/
├── http-demo/          # Streamable HTTP 版（之前创建的 weather demo）
│   └── server.py
└── stdio-demo/         # ← 本 demo（stdio 版）
    ├── server.py        # MCP Server 主程序
    ├── test_stdio.py   # 本地测试脚本
    └── README.md       # 本文件
```

## 本地测试

直接用 Python 管道模拟 MCP Client 调用：

```bash
cd /Users/berton/prj/mcp-demo-all/stdio-demo
python3 test_stdio.py
```

## 接入 knot-cli

在 `~/.bg-agent/mcp_config.json` 中添加：

```json
{
  "mcpServers": {
    "stdio-calc": {
      "command": "/usr/bin/python3",
      "args": ["/Users/berton/prj/mcp-demo-all/stdio-demo/server.py"]
    }
  }
}
```

> **注意**：stdio 类型不需要 `url` 和 `transportType` 字段，
> 只需要 `command` + `args` 告诉 knot-cli 如何启动子进程。

## 接入 Claude Desktop / Cursor

在对应配置文件的 `mcpServers` 中添加：

```json
{
  "stdio-calc": {
    "command": "/usr/bin/python3",
    "args": ["/Users/berton/prj/mcp-demo-all/stdio-demo/server.py"]
  }
}
```

## stdio 协议说明

```
MCP Client (knot-cli / Claude Desktop)
    │
    │  启动子进程: python3 server.py
    │
    ▼
stdio Server (server.py)
    ▲
    │  stdin  ←  JSON-RPC 请求（一行一个）
    │  stdout →  JSON-RPC 响应（一行一个）
    │  stderr →  日志输出（不影响协议）
```

### 通信示例

**Client → Server (写入 stdin):**
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}
```

**Server → Client (写入 stdout):**
```json
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","serverInfo":{"name":"stdio-calc-demo","version":"1.0.0"},"capabilities":{"tools":{}}}}
```

## 与 HTTP 版对比

| 特性 | stdio 版（本 demo） | HTTP 版（weather demo） |
|------|-------------------|------------------------|
| 传输方式 | stdin / stdout | HTTP POST |
| 是否需要端口 | ❌ 不需要 | ✅ 需要（如 8080） |
| 启动方式 | Client 启动子进程 | Server 常驻，Client 连接 |
| 适用场景 | 本地工具、CLI 集成 | 远程服务、跨网络 |
| 配置方式 | `command` + `args` | `url` + `transportType` |
| 并发能力 | 单进程串行 | 支持并发请求 |
| 调试难度 | 较简单（直接看 stdin/stdout） | 需抓包或 curl 调试 |
