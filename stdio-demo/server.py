#!/usr/bin/env python3
"""
MCP stdio Demo - 计算器服务（带日志版）
使用 stdio 传输方式，通过标准输入输出与 MCP Client 通信
基于手动实现 JSON-RPC，传输方式由 Client 决定，Server 无需指定 transport

日志说明：
  - 所有日志输出到 stderr（不影响 stdout 的 JSON-RPC 通信）
  - 日志格式：[TIMESTAMP] 🔵 REQUEST / 🟢 RESPONSE + 内容
  - 启动时会在 stderr 打印 "✅ stdio-calc 日志系统已启动"
"""

import sys
import json
import logging
from typing import Any

# ── 配置日志：输出到 stderr ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,  # ← 关键：日志写 stderr，不污染 stdout
)
logger = logging.getLogger("stdio-calc")

def pretty_json(data: dict) -> str:
    """美化 JSON 输出（截断过长内容）"""
    s = json.dumps(data, ensure_ascii=False, indent=2)
    if len(s) > 500:
        s = s[:500] + f"\n... (共 {len(s)} 字符，已截断)"
    return s

# 模拟计算工具
def add(a: float, b: float) -> float:
    return a + b

def subtract(a: float, b: float) -> float:
    return a - b

def multiply(a: float, b: float) -> float:
    return a * b

def divide(a: float, b: float) -> dict:
    if b == 0:
        return {"error": "除数不能为0"}
    return {"result": a / b}

def power(a: float, b: float) -> float:
    return a ** b

# 工具定义（MCP tools/list 时返回）
TOOLS = [
    {
        "name": "add",
        "description": "两数相加",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个数"},
                "b": {"type": "number", "description": "第二个数"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "subtract",
        "description": "两数相减 (a - b)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "被减数"},
                "b": {"type": "number", "description": "减数"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "multiply",
        "description": "两数相乘",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个数"},
                "b": {"type": "number", "description": "第二个数"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "divide",
        "description": "两数相除 (a / b)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "被除数"},
                "b": {"type": "number", "description": "除数"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "power",
        "description": "幂运算 (a 的 b 次方)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "底数"},
                "b": {"type": "number", "description": "指数"}
            },
            "required": ["a", "b"]
        }
    }
]

def handle_request(request: dict) -> dict:
    """处理 MCP JSON-RPC 请求（带日志）"""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    # ── 日志：打印收到的请求 ──
    logger.info(f"📨 [MCP REQUEST] id={req_id}  method={method}")
    if params:
        logger.info(f"   Params: {pretty_json(params)}")

    response = None

    # ── initialize ──────────────────────────────────────────────
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "stdio-calc-demo", "version": "1.0.0"},
                "capabilities": {"tools": {}}
            }
        }
        logger.info(f"📩 [MCP RESPONSE] id={req_id} ← initialize 成功")

    # ── notifications/initialized ───────────────────────────────
    elif method == "notifications/initialized":
        logger.info("✅ [NOTIFICATION] client 已初始化完成")
        return None  # 通知无响应

    # ── tools/list ──────────────────────────────────────────────
    elif method == "tools/list":
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS}
        }
        tool_names = [t["name"] for t in TOOLS]
        logger.info(f"📩 [MCP RESPONSE] id={req_id} ← tools/list: {tool_names}")

    # ── tools/call ──────────────────────────────────────────────
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        logger.info(f"🔵 [TOOL CALL] {tool_name}  args={arguments}")

        try:
            if tool_name == "add":
                result = add(arguments["a"], arguments["b"])
                text = json.dumps({"result": result}, ensure_ascii=False)
            elif tool_name == "subtract":
                result = subtract(arguments["a"], arguments["b"])
                text = json.dumps({"result": result}, ensure_ascii=False)
            elif tool_name == "multiply":
                result = multiply(arguments["a"], arguments["b"])
                text = json.dumps({"result": result}, ensure_ascii=False)
            elif tool_name == "divide":
                result = divide(arguments["a"], arguments["b"])
                if "error" in result:
                    response = {
                        "jsonrpc": "2.0", "id": req_id,
                        "result": {"content": [{"type": "text", "text": result["error"]}], "isError": True}
                    }
                    logger.info(f"🟠 [TOOL RESULT] {tool_name} → 错误: {result['error']}")
                else:
                    text = json.dumps({"result": result["result"]}, ensure_ascii=False)
            elif tool_name == "power":
                result = power(arguments["a"], arguments["b"])
                text = json.dumps({"result": result}, ensure_ascii=False)
            else:
                response = {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"未知工具: {tool_name}"}], "isError": True}
                }
                logger.info(f"🔴 [TOOL RESULT] 未知工具: {tool_name}")

            # 成功路径（未在上面设置 response 的情况）
            if response is None:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": text}],
                        "isError": False
                    }
                }
                logger.info(f"🟢 [TOOL RESULT] {tool_name} → {text}")

        except Exception as e:
            response = {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": str(e)}], "isError": True}
            }
            logger.info(f"🔴 [TOOL ERROR] {tool_name} → {e}")

    # ── 未知方法 ──────────────────────────────────────────────
    else:
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }
        logger.info(f"🔴 [MCP ERROR] 未知方法: {method}")

    # ── 日志：打印发送的响应 ──
    if response is not None:
        logger.info(f"📩 [MCP RESPONSE] id={response.get('id')} ← {pretty_json(response)}")

    return response


def main():
    """主循环：从 stdin 读一行 JSON，处理，写一行 JSON 到 stdout"""
    logger.info("✅ stdio-calc MCP Server 启动（日志系统已启动）")
    logger.info("   等待 knot-cli / Claude Desktop 等 Client 通过 stdio 连接...")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"🔴 JSON 解析错误: {e}  原始内容: {line[:200]}")
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    logger.info("👋 stdio-calc MCP Server 关闭")

if __name__ == "__main__":
    main()