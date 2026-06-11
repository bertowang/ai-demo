#!/usr/bin/env python3
"""
MCP Server - 浏览器自动化（stdio 传输）
使用 Playwright 提供网页截图、内容提取等能力
"""

import asyncio
import json
import base64
from mcp.server.fastmcp import FastMCP

# 创建 MCP Server
mcp = FastMCP("browser-automation")

# 全局浏览器状态
browser_context = {
    "page": None,
    "browser": None,
    "playwright": None
}


async def get_page():
    """获取或创建浏览器页面"""
    if browser_context["page"] is None:
        try:
            from playwright.async_api import async_playwright
            
            if browser_context["playwright"] is None:
                browser_context["playwright"] = await async_playwright().start()
            
            if browser_context["browser"] is None:
                browser_context["browser"] = await browser_context["playwright"].chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
            
            page = await browser_context["browser"].new_page()
            browser_context["page"] = page
            print("✅ 浏览器已启动（headless 模式）", flush=True)
        
        except ImportError:
            return None, "❌ Playwright 未安装，请运行: pip install playwright && playwright install chromium"
        except Exception as e:
            return None, f"❌ 浏览器启动失败: {str(e)}"
    
    return browser_context["page"], None


async def cleanup():
    """清理浏览器资源"""
    if browser_context["browser"]:
        await browser_context["browser"].close()
        browser_context["browser"] = None
    if browser_context["playwright"]:
        await browser_context["playwright"].stop()
        browser_context["playwright"] = None
    browser_context["page"] = None


@mcp.tool()
async def browse_url(url: str, wait_time: int = 3) -> str:
    """访问指定 URL 并获取页面标题和 URL
    
    Args:
        url: 要访问的网页地址（必须以 http:// 或 https:// 开头）
        wait_time: 等待页面加载的时间（秒），默认 3 秒
    
    Returns:
        页面标题和当前 URL
    """
    page, error = await get_page()
    if error:
        return error
    
    try:
        # 验证 URL
        if not url.startswith(("http://", "https://")):
            return "❌ URL 必须以 http:// 或 https:// 开头"
        
        print(f"🌐 正在访问: {url}", flush=True)
        
        # 访问页面
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # 等待页面加载
        await asyncio.sleep(wait_time)
        
        # 获取页面信息
        title = await page.title()
        current_url = page.url
        status = response.status if response else "unknown"
        
        result = f"""✅ 页面访问成功

📄 标题: {title}
🔗 URL: {current_url}
📊 状态码: {status}
"""
        return result
    
    except Exception as e:
        return f"❌ 访问页面失败: {str(e)}"


@mcp.tool()
async def get_page_content() -> str:
    """获取当前页面的文本内容
    
    Returns:
        页面的文本内容（截取前 5000 字符）
    """
    page, error = await get_page()
    if error:
        return error
    
    try:
        # 获取页面文本
        content = await page.evaluate("""
            () => {
                // 移除 script 和 style 标签
                const clone = document.cloneNode(true);
                clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                return clone.body?.innerText || clone.body?.textContent || '';
            }
        """)
        
        # 清理空白字符
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        cleaned = '\n'.join(lines)
        
        # 截取前 5000 字符
        if len(cleaned) > 5000:
            cleaned = cleaned[:5000] + "\n\n... (内容过长，已截断，共 {} 字符)".format(len(content))
        
        return f"📄 页面文本内容:\n\n{cleaned}"
    
    except Exception as e:
        return f"❌ 获取页面内容失败: {str(e)}"


@mcp.tool()
async def screenshot(output_path: str = None) -> str:
    """对当前页面截图
    
    Args:
        output_path: 截图保存路径（可选，默认保存到桌面）
    
    Returns:
        截图文件路径或 base64 编码的图片
    """
    page, error = await get_page()
    if error:
        return error
    
    try:
        import pathlib
        
        # 默认保存到桌面
        if not output_path:
            desktop = pathlib.Path.home() / "Desktop"
            output_path = str(desktop / "screenshot.png")
        
        # 截图
        await page.screenshot(path=output_path, full_page=False)
        
        return f"📸 截图已保存: {output_path}"
    
    except Exception as e:
        return f"❌ 截图失败: {str(e)}"


@mcp.tool()
async def click_element(selector: str) -> str:
    """点击页面上的元素
    
    Args:
        selector: CSS 选择器（如 "#id", ".class", "button" 等）
    
    Returns:
        操作结果
    """
    page, error = await get_page()
    if error:
        return error
    
    try:
        await page.click(selector, timeout=5000)
        await asyncio.sleep(1)  # 等待页面响应
        
        return f"✅ 已点击元素: {selector}"
    
    except Exception as e:
        return f"❌ 点击失败: {str(e)}\n提示: 请检查选择器是否正确，或元素是否可见"


@mcp.tool()
async def fill_input(selector: str, text: str) -> str:
    """在输入框中填写文本
    
    Args:
        selector: 输入框的 CSS 选择器
        text: 要填写的文本
    
    Returns:
        操作结果
    """
    page, error = await get_page()
    if error:
        return error
    
    try:
        await page.fill(selector, text)
        
        return f"✅ 已填写文本到: {selector}"
    
    except Exception as e:
        return f"❌ 填写失败: {str(e)}"


@mcp.tool()
async def search_text(text: str) -> str:
    """在页面中搜索指定文本
    
    Args:
        text: 要搜索的文本
    
    Returns:
        包含该文本的页面片段
    """
    page, error = await get_page()
    if error:
        return error
    
    try:
        # 获取页面文本
        content = await page.evaluate("""
            () => {
                const clone = document.cloneNode(true);
                clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                return clone.body?.innerText || '';
            }
        """)
        
        # 搜索
        if text in content:
            # 找到文本，返回上下文
            index = content.find(text)
            start = max(0, index - 100)
            end = min(len(content), index + len(text) + 100)
            snippet = content[start:end]
            
            return f"✅ 找到文本 '{text}':\n\n...{snippet}..."
        else:
            return f"❌ 页面中未找到文本: '{text}'"
    
    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"


@mcp.tool()
async def execute_javascript(code: str) -> str:
    """在页面中执行 JavaScript 代码
    
    Args:
        code: 要执行的 JavaScript 代码
    
    Returns:
        执行结果（JSON 序列化）
    """
    page, error = await get_page()
    if error:
        return error
    
    try:
        result = await page.evaluate(code)
        
        return f"✅ JavaScript 执行结果:\n\n{json.dumps(result, ensure_ascii=False, indent=2)}"
    
    except Exception as e:
        return f"❌ JavaScript 执行失败: {str(e)}"


@mcp.tool()
async def close_browser() -> str:
    """关闭浏览器
    
    Returns:
        操作结果
    """
    try:
        await cleanup()
        return "✅ 浏览器已关闭"
    except Exception as e:
        return f"❌ 关闭浏览器失败: {str(e)}"


if __name__ == "__main__":
    import atexit
    
    # 注册退出清理
    def cleanup_sync():
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cleanup())
        loop.close()
    
    atexit.register(cleanup_sync)
    
    # 启动 MCP Server
    print("🚀 Browser Automation MCP Server 启动（stdio 模式）", flush=True)
    print("📝 提示: 首次使用需要安装 Playwright: pip install playwright && playwright install chromium", flush=True)
    mcp.run()
