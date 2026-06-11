# Weather MCP Demo

一个最简单的 MCP Server 示例，提供天气查询能力。

## 快速开始

```bash
# 1. 创建虚拟环境并激活
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python server.py
```

启动后访问端点：`http://127.0.0.1:8080/mcp`

## 提供的工具

- `get_weather(city)` — 查询某城市天气
- `list_cities()` — 列出支持的城市

## 接入 Knot CLI（本地测试）

编辑 `~/.bg-agent/mcp_config.json`：

```json
{
  "mcpServers": {
    "weather": {
      "url": "http://127.0.0.1:8080/mcp",
      "transportType": "streamable-http",
      "timeout": 60
    }
  }
}
```

## 上传到 Knot MCP 市场

1. 访问 <https://knot.woa.com/mcp-servers/market>
2. 点击「+ 新建 MCP」
3. 连接方式选 `Streamable HTTP`
4. 服务配置粘贴：
   ```json
   {
     "mcpServers": {
       "weather": { "url": "https://你的部署地址/mcp" }
     }
   }
   ```

## 手动验证

启动服务后另起终端运行：

```bash
# 1) 初始化（注意拿到响应头中的 Mcp-Session-Id）
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  http://127.0.0.1:8080/mcp \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","clientInfo":{"name":"test","version":"0.0.1"},"capabilities":{}}}'

# 2) 通知 initialized（替换 <SID>）
curl -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: <SID>' \
  http://127.0.0.1:8080/mcp \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'

# 3) 列出工具
curl -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: <SID>' \
  http://127.0.0.1:8080/mcp \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# 4) 调用工具
curl -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'mcp-session-id: <SID>' \
  http://127.0.0.1:8080/mcp \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_weather","arguments":{"city":"北京"}}}'
```
