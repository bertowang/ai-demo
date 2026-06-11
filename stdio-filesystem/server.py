#!/usr/bin/env python3
"""
stdio-filesystem MCP Server（带日志版）
提供本地文件系统操作能力（只读 + 写文件，带白名单安全限制）
传输方式：stdio（由 MCP Client 作为子进程启动）

日志说明：
  - 所有日志输出到 stderr（不影响 MCP 的 stdio JSON-RPC 通信）
  - 日志格式：[TIMESTAMP] 🔵 REQUEST / 🟢 RESPONSE + 内容
  - 每个工具调用都会打印参数和返回结果
"""

import os
import json
import sys
import glob
import logging
import mimetypes
from pathlib import Path
from typing import Any

# ── 配置日志：输出到 stderr ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,  # ← 关键：日志写 stderr，不污染 stdout
)
logger = logging.getLogger("stdio-filesystem")

def pretty_json(data: Any) -> str:
    """美化 JSON 输出（截断过长内容）"""
    s = json.dumps(data, ensure_ascii=False, indent=2) if not isinstance(data, str) else data
    if len(s) > 500:
        s = s[:500] + f"\n... (共 {len(s)} 字符，已截断)"
    return s

from mcp.server.fastmcp import FastMCP

# ── 安全白名单：只允许操作这些目录下的文件 ──────────────────────────────
ALLOWED_DIRS = [
    "/Users/berton/prj",
    "/tmp",
]

def is_path_allowed(path: str) -> bool:
    """检查路径是否在白名单内"""
    resolved = Path(path).resolve()
    for allowed in ALLOWED_DIRS:
        try:
            resolved.relative_to(Path(allowed).resolve())
            return True
        except ValueError:
            continue
    return False

def reject_if_not_allowed(path: str):
    if not is_path_allowed(path):
        raise ValueError(f"路径不在允许范围内: {path}\n允许的目录: {ALLOWED_DIRS}")

# ── 创建 MCP Server ────────────────────────────────────────────────────────
mcp = FastMCP("filesystem-mcp", instructions="文件系统操作服务（带日志版）")

# ── 工具 1：列出目录内容 ────────────────────────────────────────────────────
@mcp.tool()
def list_dir(path: str) -> str:
    """列出指定目录下的文件和子目录。
    
    Args:
        path: 目录路径，例如 "/Users/berton/prj"
    
    Returns:
        目录内容列表（标记文件/目录类型）
    """
    logger.info(f"🔵 [TOOL CALL] list_dir  path={path!r}")
    reject_if_not_allowed(path)
    p = Path(path)
    if not p.exists():
        result = f"错误：路径不存在: {path}"
        logger.info(f"🟠 [TOOL RESULT] list_dir → {result}")
        return result
    if not p.is_dir():
        result = f"错误：不是一个目录: {path}"
        logger.info(f"🟠 [TOOL RESULT] list_dir → {result}")
        return result

    entries = []
    for entry in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        if entry.is_dir():
            entries.append(f"[DIR]  {entry.name}/")
        elif entry.is_file():
            size = entry.stat().st_size
            size_str = f"{size} bytes" if size < 10240 else f"{size//1024} KB"
            entries.append(f"[FILE] {entry.name}  ({size_str})")
        else:
            entries.append(f"[OTHER] {entry.name}")

    result = "\n".join(entries) if entries else "(空目录)"
    logger.info(f"🟢 [TOOL RESULT] list_dir → {len(entries)} 个条目")
    return result

# ── 工具 2：读取文件内容 ────────────────────────────────────────────────────
@mcp.tool()
def read_file(path: str, max_lines: int = 200) -> str:
    """读取文本文件的内容。
    
    Args:
        path: 文件路径
        max_lines: 最多读取行数（默认 200，防止大文件）
    
    Returns:
        文件内容（前 max_lines 行）
    """
    logger.info(f"🔵 [TOOL CALL] read_file  path={path!r}  max_lines={max_lines}")
    reject_if_not_allowed(path)
    p = Path(path)
    if not p.exists():
        result = f"错误：文件不存在: {path}"
        logger.info(f"🟠 [TOOL RESULT] read_file → {result}")
        return result
    if not p.is_file():
        result = f"错误：不是一个文件: {path}"
        logger.info(f"🟠 [TOOL RESULT] read_file → {result}")
        return result

    # 尝试判断是否为文本文件
    mime, _ = mimetypes.guess_type(str(p))
    if mime and not mime.startswith("text") and mime not in ("application/json", "application/xml"):
        result = f"警告：文件可能不是文本文件 (MIME: {mime})，已拒绝读取。如需读取，请使用二进制工具。"
        logger.info(f"🟠 [TOOL RESULT] read_file → {result}")
        return result

    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        content = "\n".join(lines[:max_lines])
        if len(lines) > max_lines:
            content += f"\n\n... (共 {len(lines)} 行，仅显示前 {max_lines} 行)"
        logger.info(f"🟢 [TOOL RESULT] read_file → {len(lines)} 行，显示 {max_lines} 行")
        return content
    except Exception as e:
        result = f"读取失败: {e}"
        logger.info(f"🟠 [TOOL RESULT] read_file → {result}")
        return result

# ── 工具 3：写入文件 ────────────────────────────────────────────────────────
@mcp.tool()
def write_file(path: str, content: str, mode: str = "overwrite") -> str:
    """写入内容到文件（仅允许写入白名单目录）。
    
    Args:
        path: 文件路径
        content: 要写入的内容
        mode: 写入模式，"overwrite" 覆盖，"append" 追加
    
    Returns:
        操作结果
    """
    logger.info(f"🔵 [TOOL CALL] write_file  path={path!r}  mode={mode!r}  content={len(content)} 字符")
    reject_if_not_allowed(path)
    p = Path(path)

    # 不允许覆盖非白名单文件（已在 reject_if_not_allowed 中处理）
    try:
        if mode == "append" and p.exists():
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
            result = f"追加成功: {path}（原大小 {p.stat().st_size} bytes）"
            logger.info(f"🟢 [TOOL RESULT] write_file → {result}")
            return result
        else:
            p.write_text(content, encoding="utf-8")
            result = f"写入成功: {path}（{len(content)} 字符）"
            logger.info(f"🟢 [TOOL RESULT] write_file → {result}")
            return result
    except Exception as e:
        result = f"写入失败: {e}"
        logger.info(f"🟠 [TOOL RESULT] write_file → {result}")
        return result

# ── 工具 4：搜索文件（按文件名 glob）───────────────────────────────────────
@mcp.tool()
def search_files(base_path: str, pattern: str) -> str:
    """在指定目录下按 glob 模式搜索文件（支持递归）。
    
    Args:
        base_path: 搜索起点目录，例如 "/Users/berton/prj"
        pattern: glob 模式。
                 非递归例："*.py"（仅当前目录）
                 递归例："**/*.py"（包含所有子目录）
    
    Returns:
        匹配的文件路径列表（最多 50 个）
    """
    logger.info(f"🔵 [TOOL CALL] search_files  base_path={base_path!r}  pattern={pattern!r}")
    reject_if_not_allowed(base_path)
    p = Path(base_path)
    if not p.exists() or not p.is_dir():
        result = f"错误：无效目录: {base_path}"
        logger.info(f"🟠 [TOOL RESULT] search_files → {result}")
        return result

    try:
        # 如果 pattern 不含 **，自动前缀以支持递归搜索
        if "**" not in pattern:
            pattern = "**/" + pattern
        matches = list(p.glob(pattern))
        if not matches:
            result = f"未找到匹配 '{pattern}' 的文件（搜索目录: {base_path}）"
            logger.info(f"🟠 [TOOL RESULT] search_files → {result}")
            return result
        results = [str(m.resolve()) for m in sorted(matches)[:50]]
        suffix = f"\n\n... 共 {len(matches)} 个结果，仅显示前 50 个" if len(matches) > 50 else ""
        result = "\n".join(results) + suffix
        logger.info(f"🟢 [TOOL RESULT] search_files → {len(matches)} 个匹配，显示 50 个")
        return result
    except Exception as e:
        result = f"搜索失败: {e}"
        logger.info(f"🟠 [TOOL RESULT] search_files → {result}")
        return result

# ── 工具 5：获取文件/目录信息 ────────────────────────────────────────────────
@mcp.tool()
def get_info(path: str) -> str:
    """获取文件或目录的详细信息（大小、修改时间等）。
    
    Args:
        path: 文件或目录路径
    
    Returns:
        详细信息字典的 JSON 字符串
    """
    logger.info(f"🔵 [TOOL CALL] get_info  path={path!r}")
    reject_if_not_allowed(path)
    p = Path(path)
    if not p.exists():
        result = f"错误：路径不存在: {path}"
        logger.info(f"🟠 [TOOL RESULT] get_info → {result}")
        return result

    stat = p.stat()
    info = {
        "path": str(p.resolve()),
        "type": "directory" if p.is_dir() else "file",
        "size_bytes": stat.st_size if p.is_file() else None,
        "size_human": f"{stat.st_size} bytes" if p.is_file() else None,
        "modified": stat.st_mtime,
    }
    result = json.dumps(info, indent=2, ensure_ascii=False)
    logger.info(f"🟢 [TOOL RESULT] get_info → {pretty_json(info)}")
    return result

# ── 启动 Server（stdio 模式）───────────────────────────────────────────────
if __name__ == "__main__":
    # stdio 模式：从 stdin 读取 JSON-RPC 请求，向 stdout 输出响应
    mcp.run(transport="stdio")