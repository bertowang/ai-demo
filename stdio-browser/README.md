# Browser Automation MCP Server（stdio 版）

## 功能说明

这是一个基于 stdio 传输的 MCP Server，提供 **浏览器自动化能力**（基于 Playwright）。

## 提供的工具

| 工具 | 功能 |
|------|------|
| `browse_url` | 访问指定 URL 并获取页面信息 |
| `get_page_content` | 获取当前页面的文本内容 |
| `screenshot` | 对当前页面截图 |
| `click_element` | 点击页面上的元素 |
| `fill_input` | 在输入框中填写文本 |
| `search_text` | 在页面中搜索指定文本 |
| `execute_javascript` | 在页面中执行 JavaScript 代码 |
| `close_browser` | 关闭浏览器 |

## 使用方法

### 1. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置到 knot-cli

编辑 `~/.bg-agent/mcp_config.json`:

```json
{
  "mcpServers": {
    "browser": {
      "command": "/Users/berton/prj/mcp-demo-all/stdio-browser/venv/bin/python",
      "args": ["/Users/berton/prj/mcp-demo-all/stdio-browser/server.py"],
      "transportType": "stdio"
    }
  }
}
```

### 3. 使用示例

配置完成后，在 knot-cli 中可以：

```
帮我访问 https://www.baidu.com 并截图
获取当前页面的文本内容
在搜索框中输入 "MCP 协议" 并搜索
点击页面上的 "新闻" 链接
```

## 注意事项

- ⚠️ 浏览器运行在 headless 模式（无界面），适合自动化任务
- ⚠️ 首次使用需要安装 Playwright 浏览器：`playwright install chromium`
- ⚠️ 某些网站可能有反爬虫机制，访问可能被拒绝
- ⚠️ 页面加载时间可能因网络状况而异，可适当调整 `wait_time` 参数

## 典型应用场景

1. **网页截图**: 自动截取网页截图保存
2. **内容提取**: 抓取网页文本内容进行分析
3. **表单自动填写**: 自动填写网页表单
4. **网页监控**: 定期检查网页内容变化
5. **自动化测试**: 模拟用户操作进行简单测试

## 目录结构

```
stdio-browser/
├── server.py           # MCP Server 主程序
├── requirements.txt    # 依赖列表
└── README.md          # 本文档
```

## 故障排查

### Playwright 未安装

```
❌ Playwright 未安装，请运行: pip install playwright && playwright install chromium
```

**解决**: 按照提示安装 Playwright 和浏览器

### 浏览器启动失败

可能是系统依赖缺失（Linux），需要安装：

```bash
# Ubuntu/Debian
sudo apt-get install libgtk-3-0 libgbm1 libasound2

# CentOS/RHEL
sudo yum install gtk3 mesa-libgbm alsa-lib
```

### 页面访问超时

增加 `wait_time` 参数，或检查网络连接。
