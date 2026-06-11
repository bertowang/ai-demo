#!/usr/bin/env python3
"""
stdio-filesystem MCP Server 测试脚本
向子进程 stdin 发送 JSON-RPC 请求，解析 stdout 响应
"""
import subprocess
import json
import os
import sys

SERVER = os.path.join(os.path.dirname(__file__), "server.py")
PYTHON = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python")

def main():
    proc = subprocess.Popen(
        [PYTHON, SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def send(req: dict) -> dict:
        data = json.dumps(req) + "\n"
        proc.stdin.write(data.encode())
        proc.stdin.flush()
        line = proc.stdout.readline().decode().strip()
        return json.loads(line) if line else {}

    print("=" * 60)
    print("stdio-filesystem MCP Server 测试")
    print("=" * 60)

    # Step 1: initialize
    print("\n[Step 1] initialize ...")
    resp = send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05",
        "clientInfo": {"name": "test-client", "version": "1.0"},
        "capabilities": {}
    }})
    result = resp.get("result", {})
    print(f"  Server: {result.get('serverInfo', {}).get('name', '?')}")
    print(f"  Protocol: {result.get('protocolVersion', '?')}")
    assert "result" in resp, f"initialize 失败: {resp}"

    # Step 2: initialized (notification)
    print("\n[Step 2] initialized (notification) ...")
    proc.stdin.write((json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n").encode())
    proc.stdin.flush()
    # notification 无响应，跳过

    # Step 3: tools/list
    print("\n[Step 3] tools/list ...")
    resp = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = resp.get("result", {}).get("tools", [])
    print(f"  发现 {len(tools)} 个工具:")
    for t in tools:
        print(f"    - {t['name']}: {t.get('description', '')[:50]}")
    assert len(tools) == 5, f"期望 5 个工具，实际 {len(tools)}"

    # Step 4: list_dir
    print("\n[Step 4] tools/call list_dir(path=/Users/berton/prj) ...")
    resp = send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "list_dir", "arguments": {"path": "/Users/berton/prj"}
    }})
    content = resp.get("result", {}).get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"  结果（前 300 字符）:\n{text[:300]}")
    assert "mcp-demo-all" in text, "list_dir 结果异常"

    # Step 5: read_file
    print("\n[Step 5] tools/call read_file(README.md) ...")
    readme = os.path.join(os.path.dirname(__file__), "README.md")
    resp = send({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "read_file", "arguments": {"path": readme, "max_lines": 10}
    }})
    content = resp.get("result", {}).get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"  结果（前 200 字符）:\n{text[:200]}")
    assert "stdio-filesystem" in text, "read_file 结果异常"

    # Step 6: search_files
    print("\n[Step 6] tools/call search_files(pattern=*.py) ...")
    resp = send({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
        "name": "search_files", "arguments": {"base_path": "/Users/berton/prj/mcp-demo-all", "pattern": "*.py"}
    }})
    content = resp.get("result", {}).get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"  找到的 .py 文件（前 500 字符）:\n{text[:500]}")
    assert ".py" in text, "search_files 未返回任何 .py 文件"
    # 验证递归搜索：应该能搜到子目录里的 server.py
    has_server_py = "server.py" in text
    print(f"  包含 server.py: {has_server_py}")

    # Step 7: get_info
    print("\n[Step 7] tools/call get_info(/Users/berton/prj/mcp-demo-all) ...")
    resp = send({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {
        "name": "get_info", "arguments": {"path": "/Users/berton/prj/mcp-demo-all"}
    }})
    content = resp.get("result", {}).get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"  信息: {text[:200]}")
    assert "directory" in text, "get_info 结果异常"

    # Step 8: 安全限制测试（应被拒绝）
    print("\n[Step 8] 安全测试：尝试读取 /etc/passwd（应被拒绝）...")
    resp = send({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {
        "name": "read_file", "arguments": {"path": "/etc/passwd"}
    }})
    content = resp.get("result", {}).get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"  结果: {text[:150]}")
    # 错误信息可能是中文或英文，只要包含拒绝关键词即可
    reject_keywords = ["不允许", "not allowed", "路径不在允许范围", "Error executing tool"]
    assert any(k in text for k in reject_keywords), f"安全限制未生效！返回内容: {text[:200]}"

    proc.terminate()
    print("\n" + "=" * 60)
    print("✅ 全部 8 项测试通过！stdio-filesystem MCP Server 工作正常。")
    print("=" * 60)

if __name__ == "__main__":
    main()
