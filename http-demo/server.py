"""
Weather MCP Demo
================
一个最简单的 MCP Server 示例，提供天气查询能力。
使用 FastMCP 框架，Streamable HTTP 协议。

启动后端点：http://127.0.0.1:8080/mcp

日志说明：
  - 所有 MCP 请求/响应都会打印到终端
  - 日志格式：[TIMESTAMP] 🔵 REQUEST / 🟢 RESPONSE + 内容
"""

import logging
import json
from fastmcp import FastMCP

# ── 配置日志 ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("weather-mcp")

# 用于美化打印 JSON 的辅助函数
def pretty_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)

# ── 创建 MCP Server 实例 ──────────────────────────────────────────────────
mcp = FastMCP("weather-mcp", instructions="天气查询服务（带日志版）")

# 模拟天气数据（demo 用，生产可替换为真实 API）
WEATHER_DATA = {
    "北京": {"temp": 22, "weather": "晴", "humidity": "45%"},
    "上海": {"temp": 26, "weather": "多云", "humidity": "60%"},
    "深圳": {"temp": 30, "weather": "雷阵雨", "humidity": "78%"},
    "成都": {"temp": 24, "weather": "阴", "humidity": "70%"},
    "广州": {"temp": 29, "weather": "小雨", "humidity": "82%"},
    "杭州": {"temp": 25, "weather": "晴转多云", "humidity": "65%"},
}


@mcp.tool()
def get_weather(city: str) -> dict:
    """
    查询指定城市的实时天气

    Args:
        city: 城市名称，例如：北京、上海、深圳

    Returns:
        包含温度、天气、湿度的字典；若城市不支持，返回 error 与受支持城市列表
    """
    # ── 日志：记录工具被调用 ──
    logger.info(f"🔵 [TOOL CALL] get_weather  city={city!r}")

    if city not in WEATHER_DATA:
        result = {
            "error": f"暂不支持城市：{city}",
            "supported": list(WEATHER_DATA.keys()),
        }
        logger.info(f"🟠 [TOOL RESULT] get_weather → {pretty_json(result)}")
        return result

    data = WEATHER_DATA[city]
    result = {
        "city": city,
        "temperature": f"{data['temp']}°C",
        "weather": data["weather"],
        "humidity": data["humidity"],
    }

    # ── 日志：记录工具返回结果 ──
    logger.info(f"🟢 [TOOL RESULT] get_weather → {pretty_json(result)}")
    return result


@mcp.tool()
def list_cities() -> list:
    """列出所有支持查询的城市名称"""
    logger.info("🔵 [TOOL CALL] list_cities")
    cities = list(WEATHER_DATA.keys())
    logger.info(f"🟢 [TOOL RESULT] list_cities → {cities}")
    return cities


# ── MCP 请求/响应日志钩子（FastMCP 3.x 支持） ──────────────────────────
# 通过装饰 mcp._mcp_request 来拦截所有进入 MCP 的请求
# 注意：这是 FastMCP 内部钩子，不同版本接口可能略有差异
_original_handle = None

def enable_request_logging(mcp_server):
    """为 MCP Server 注入请求/响应日志（通过 http_app 获取底层 Starlette app）"""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class MCPLoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # 只记录 POST /mcp 的请求
            if request.method == "POST" and "/mcp" in str(request.url.path):
                # 需要「复制」body，因为 Starlette 的 body 只能读一次
                body_bytes = await request.body()
                try:
                    req_json = json.loads(body_bytes)
                    req_id = req_json.get("id", "?")
                    method = req_json.get("method", "?")
                    params = req_json.get("params", {})
                    logger.info(f"📨 [MCP REQUEST]  id={req_id}  method={method}")
                    logger.info(f"   Params: {pretty_json(params) if params else '(空)'}")
                    # 打印完整请求（截断过长内容）
                    full = json.dumps(req_json, ensure_ascii=False)
                    if len(full) > 2000:
                        full = full[:2000] + f"...(共{len(full)}字符)"
                    logger.info(f"   [完整请求] {full}")
                except Exception:
                    logger.info(f"📨 [MCP REQUEST]  (非 JSON) body={body_bytes[:200]}")

            response = await call_next(request)

            # 尝试读取并记录响应 body
            if request.method == "POST" and "/mcp" in str(request.url.path):
                logger.info(f"📩 [MCP RESPONSE] status={response.status_code}")
                # 注意：response body 可能已被流式发送，这里只能记录状态码
                # 工具返回值会在工具函数内部打印（见 get_weather / list_cities）

            return response

    # FastMCP 3.x: 通过 http_app 属性获取底层 Starlette app
    app = mcp_server.http_app()
    app.add_middleware(MCPLoggingMiddleware)
    logger.info("✅ MCP 请求日志中间件已挂载")

if __name__ == "__main__":
    # 挂载日志中间件
    enable_request_logging(mcp)

    logger.info("🚀 Weather MCP Server 启动中...")
    logger.info("   端点: http://0.0.0.0:8080/mcp")
    logger.info("   日志: 所有 MCP 请求/响应将打印到终端")

    # Streamable HTTP 协议；端点路径必须为 /mcp
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
