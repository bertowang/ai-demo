# SQLite MCP Server（stdio 版）

## 功能说明

这是一个基于 stdio 传输的 MCP Server，提供 **安全的 SQLite 数据库查询能力**。

## 提供的工具

| 工具 | 功能 |
|------|------|
| `list_tables` | 列出数据库中的所有表 |
| `describe_table` | 查看表结构（字段信息） |
| `query_data` | 执行 SELECT 查询（只读，禁止写操作） |
| `get_table_stats` | 获取表的统计信息（行数、字段数） |

## 安全特性

- ✅ 只允许 SELECT 查询
- ✅ 禁止危险关键词：DROP、DELETE、UPDATE、INSERT、ALTER、CREATE、REPLACE
- ✅ 自动初始化演示数据库（users 表 + orders 表）

## 使用方法

### 1. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 测试运行

```bash
# 直接运行（stdio 模式，等待 stdin 输入）
python server.py
```

### 3. 配置到 knot-cli

编辑 `~/.bg-agent/mcp_config.json`:

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "/Users/berton/prj/mcp-demo-all/stdio-sqlite/venv/bin/python",
      "args": ["/Users/berton/prj/mcp-demo-all/stdio-sqlite/server.py"],
      "transportType": "stdio"
    }
  }
}
```

### 4. 使用示例

配置完成后，在 knot-cli 中可以直接问：

```
我的数据库里有哪些表？
users 表的结构是什么？
查询所有年龄大于 25 岁的用户
统计 orders 表有多少条记录？
```

## 演示数据

初始化时会自动创建演示数据：

**users 表**:
| id | name | email | age | city |
|----|------|-------|-----|------|
| 1 | 张三 | zhangsan@example.com | 28 | 北京 |
| 2 | 李四 | lisi@example.com | 35 | 上海 |
| 3 | 王五 | wangwu@example.com | 22 | 深圳 |
| 4 | 赵六 | zhaoliu@example.com | 30 | 广州 |
| 5 | 钱七 | qianqi@example.com | 26 | 杭州 |

**orders 表**:
| id | user_id | product | amount | status |
|----|---------|---------|--------|--------|
| 1 | 1 | MacBook Pro | 12999.0 | completed |
| 2 | 1 | iPhone 15 | 5999.0 | completed |
| ... | ... | ... | ... | ... |

## 自定义数据库

如果要连接自己的 SQLite 数据库，修改 `server.py` 中的 `DEFAULT_DB_PATH` 变量，或在调用工具时传入 `db_path` 参数。

## 目录结构

```
stdio-sqlite/
├── server.py           # MCP Server 主程序
├── requirements.txt    # 依赖列表
├── demo.db            # 自动生成的演示数据库（运行后生成）
└── README.md          # 本文档
```
