# stdio-filesystem MCP Demo

## 功能说明

这是一个基于 **stdio 传输** 的 MCP Server，提供本地文件系统操作能力。

## 提供的工具

| 工具名 | 功能 |
|--------|------|
| `list_dir` | 列出目录内容（标记文件/目录类型） |
| `read_file` | 读取文本文件内容（默认最多 200 行） |
| `write_file` | 写入内容到文件（支持覆盖/追加） |
| `search_files` | 按 glob 模式搜索文件 |
| `get_info` | 获取文件/目录详细信息 |

## 安全限制

仅允许操作以下白名单目录（在 `server.py` 中配置）：

```python
ALLOWED_DIRS = [
    "/Users/berton/prj",
    "/tmp",
]
```

尝试操作白名单之外的路径会被拒绝。

## 本地测试（直接运行）

```bash
# 安装依赖
pip install -r requirements.txt

# 直接运行（stdio 模式，需通过 MCP Client 调用）
python server.py
```

## 通过 test_stdio.py 测试

参考 `../stdio-demo/test_stdio.py` 的写法，向 stdin 发送 JSON-RPC 请求。

示例测试脚本（`test_manual.py`）：

```python
import subprocess, json, os

proc = subprocess.Popen(
    ["python", "server.py"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    cwd=os.path.dirname(__file__)
)

def send(req):
    data = json.dumps(req) + "\n"
    proc.stdin.write(data.encode()); proc.stdin.flush()
    return json.loads(proc.stdout.readline())

# 1. initialize
print(send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
    "protocolVersion":"2024-11-05","clientInfo":{"name":"test","version":"1.0"},"capabilities":{}}}))

# 2. tools/list
print(send({"jsonrpc":"2.0","id":2,"method":"tools/list"}))

# 3. read_file
print(send({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
    "name":"list_dir","arguments":{"path":"/Users/berton/prj"}}}))

proc.terminate()
```

## 接入 knot-cli

在 `~/.bg-agent/mcp_config.json` 中添加：

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "/Users/berton/prj/mcp-demo-all/stdio-filesystem/.venv/bin/python",
      "args": ["/Users/berton/prj/mcp-demo-all/stdio-filesystem/server.py"],
      "transportType": "stdio"
    }
  }
}
```

然后在 knot-cli 中使用：

```
knot-cli chat -p "帮我看看 /Users/berton/prj/ 下有哪些目录"
```
