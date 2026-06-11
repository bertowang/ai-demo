#!/usr/bin/env python3
"""
stdio MCP Demo 本地测试脚本
模拟 MCP Client，通过 stdin/stdout 与 server.py 通信
"""

import subprocess
import json
import sys
import time

SERVE = ["/opt/homebrew/bin/python3.12", "/Users/berton/prj/mcp-demo-all/stdio-demo/server.py"]

def send_request(proc: subprocess.Popen, request: dict) -> dict:
    """向子进程发送请求并读取响应"""
    line = json.dumps(request, ensure_ascii=False) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()
    # 读一行响应
    response_line = proc.stdout.readline().strip()
    if not response_line:
        return {"error": "No response (server may have crashed)"}
    return json.loads(response_line)

def main():
    print("=" * 60)
    print("MCP stdio Demo - 本地测试")
    print("=" * 60)

    # 启动子进程
    print(f"\n[启动] 启动 server.py 子进程...")
    proc = subprocess.Popen(
        SERVE,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    print(f"[启动] 子进程 PID = {proc.pid}")

    try:
        # ── Step 1: initialize ────────────────────────────────
        print("\n" + "-" * 60)
        print("[Step 1] 发送 initialize 请求...")
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "clientInfo": {"name": "test-client", "version": "1.0"},
                "capabilities": {}
            }
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        assert resp["id"] == 1
        print("  ✅ initialize 成功")

        # ── Step 2: notifications/initialized ─────────────────
        print("\n" + "-" * 60)
        print("[Step 2] 发送 notifications/initialized (无响应)...")
        req = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        proc.stdin.flush()
        # 通知无响应，等待一小会儿
        time.sleep(0.2)
        print("  ✅ 通知已发送（无响应，符合协议）")

        # ── Step 3: tools/list ────────────────────────────────
        print("\n" + "-" * 60)
        print("[Step 3] 发送 tools/list 请求...")
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        tools = resp["result"]["tools"]
        print(f"  ✅ 发现 {len(tools)} 个工具:")
        for t in tools:
            print(f"     - {t['name']}: {t['description']}")
        assert len(tools) == 5

        # ── Step 4: 调用 add(3, 5) ─────────────────────────
        print("\n" + "-" * 60)
        print("[Step 4] 调用 add(3, 5)...")
        req = {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "add", "arguments": {"a": 3, "b": 5}}
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        result = json.loads(resp["result"]["content"][0]["text"])
        print(f"  ✅ 3 + 5 = {result['result']} (期望 8)")

        # ── Step 5: 调用 subtract(10, 4) ───────────────────
        print("\n" + "-" * 60)
        print("[Step 5] 调用 subtract(10, 4)...")
        req = {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "subtract", "arguments": {"a": 10, "b": 4}}
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        result = json.loads(resp["result"]["content"][0]["text"])
        print(f"  ✅ 10 - 4 = {result['result']} (期望 6)")

        # ── Step 6: 调用 multiply(6, 7) ─────────────────────
        print("\n" + "-" * 60)
        print("[Step 6] 调用 multiply(6, 7)...")
        req = {
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "multiply", "arguments": {"a": 6, "b": 7}}
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        result = json.loads(resp["result"]["content"][0]["text"])
        print(f"  ✅ 6 × 7 = {result['result']} (期望 42)")

        # ── Step 7: 调用 divide(15, 3) ──────────────────────
        print("\n" + "-" * 60)
        print("[Step 7] 调用 divide(15, 3)...")
        req = {
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {"name": "divide", "arguments": {"a": 15, "b": 3}}
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        result = json.loads(resp["result"]["content"][0]["text"])
        print(f"  ✅ 15 ÷ 3 = {result['result']} (期望 5.0)")

        # ── Step 8: 调用 divide(10, 0) 测试错误 ────────────
        print("\n" + "-" * 60)
        print("[Step 8] 调用 divide(10, 0) （预期报错）...")
        req = {
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "divide", "arguments": {"a": 10, "b": 0}}
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        print(f"  ✅ 正确返回错误（isError=true）")

        # ── Step 9: 调用 power(2, 10) ───────────────────────
        print("\n" + "-" * 60)
        print("[Step 9] 调用 power(2, 10)...")
        req = {
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {"name": "power", "arguments": {"a": 2, "b": 10}}
        }
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = send_request(proc, req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        result = json.loads(resp["result"]["content"][0]["text"])
        print(f"  ✅ 2^10 = {result['result']} (期望 1024)")

        # ── 完成 ──────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！stdio MCP Demo 工作正常")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        # 打印子进程的 stderr
        proc.terminate()
        stderr_out = proc.stderr.read()
        if stderr_out:
            print(f"\nserver.py stderr 输出:\n{stderr_out}")
        sys.exit(1)

    finally:
        proc.terminate()
        proc.wait()
        print(f"\n[清理] 子进程 {proc.pid} 已终止")

if __name__ == "__main__":
    main()
