#!/usr/bin/env python3
"""
MCP Server - SQLite 数据库查询（stdio 传输）
提供安全的 SQLite 数据库查询能力
"""

import asyncio
import sqlite3
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# 创建 MCP Server
mcp = FastMCP("sqlite-query")

# 默认数据库路径（可以修改为你的数据库）
DEFAULT_DB_PATH = str(Path.home() / "prj" / "mcp-demo-all" / "stdio-sqlite" / "demo.db")

# 危险操作关键词（禁止执行）
FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "REPLACE"]


def get_connection(db_path: str = None):
    """获取数据库连接"""
    path = db_path or DEFAULT_DB_PATH
    return sqlite3.connect(path)


def init_demo_db():
    """初始化演示数据库"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            age INTEGER,
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建订单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product TEXT NOT NULL,
            amount REAL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # 插入示例数据（如果表为空）
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            (1, "张三", "zhangsan@example.com", 28, "北京"),
            (2, "李四", "lisi@example.com", 35, "上海"),
            (3, "王五", "wangwu@example.com", 22, "深圳"),
            (4, "赵六", "zhaoliu@example.com", 30, "广州"),
            (5, "钱七", "qianqi@example.com", 26, "杭州"),
        ]
        cursor.executemany("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", users)
        
        orders = [
            (1, "MacBook Pro", 12999.0, "completed"),
            (1, "iPhone 15", 5999.0, "completed"),
            (2, "iPad Air", 4799.0, "pending"),
            (3, "AirPods Pro", 1899.0, "completed"),
            (4, "Apple Watch", 2999.0, "shipped"),
            (5, "Magic Keyboard", 2399.0, "pending"),
        ]
        cursor.executemany("INSERT INTO orders (user_id, product, amount, status) VALUES (?, ?, ?, ?)", orders)
    
    conn.commit()
    conn.close()
    print(f"✅ 演示数据库已初始化: {DEFAULT_DB_PATH}", flush=True)


@mcp.tool()
def list_tables(db_path: str = None) -> str:
    """列出数据库中的所有表
    
    Args:
        db_path: 数据库文件路径（可选，默认使用演示数据库）
    
    Returns:
        数据库中所有表的列表
    """
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        if not tables:
            return "数据库中没有表"
        
        return "数据库中的表:\n" + "\n".join(f"- {table}" for table in tables)
    
    except Exception as e:
        return f"❌ 列出表失败: {str(e)}"


@mcp.tool()
def describe_table(table_name: str, db_path: str = None) -> str:
    """查看表结构（字段信息）
    
    Args:
        table_name: 表名
        db_path: 数据库文件路径（可选，默认使用演示数据库）
    
    Returns:
        表的字段结构信息
    """
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            conn.close()
            return f"❌ 表 '{table_name}' 不存在"
        
        # 格式化输出
        result = f"表 '{table_name}' 的结构:\n\n"
        result += "字段名\t类型\t\t允许NULL\t默认值\t主键\n"
        result += "-" * 60 + "\n"
        
        for col in columns:
            cid, name, col_type, notnull, default, pk = col
            null_str = "NO" if notnull else "YES"
            pk_str = "YES" if pk else ""
            default_str = str(default) if default else ""
            result += f"{name}\t{col_type}\t\t{null_str}\t{default_str}\t{pk_str}\n"
        
        conn.close()
        return result
    
    except Exception as e:
        return f"❌ 查看表结构失败: {str(e)}"


@mcp.tool()
def query_data(sql: str, db_path: str = None) -> str:
    """执行 SELECT 查询（只读，禁止写操作）
    
    Args:
        sql: SELECT SQL 语句
        db_path: 数据库文件路径（可选，默认使用演示数据库）
    
    Returns:
        查询结果
    
    Note:
        为了安全，只支持 SELECT 查询，禁止 INSERT/UPDATE/DELETE/DROP 等操作
    """
    # 安全检查：禁止危险操作
    sql_upper = sql.strip().upper()
    
    if not sql_upper.startswith("SELECT"):
        return "❌ 为了安全，只支持 SELECT 查询"
    
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper:
            return f"❌ 检测到 forbidden 关键词: {keyword}，已拒绝执行"
    
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # 获取列名
        column_names = [description[0] for description in cursor.description]
        
        conn.close()
        
        if not rows:
            return "查询成功，但没有返回数据"
        
        # 格式化输出
        result = f"✅ 查询成功，共 {len(rows)} 条记录:\n\n"
        
        # 表头
        result += "\t".join(column_names) + "\n"
        result += "-" * 80 + "\n"
        
        # 数据行
        for row in rows:
            result += "\t".join(str(cell) for cell in row) + "\n"
        
        return result
    
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


@mcp.tool()
def execute_safe(sql: str, db_path: str = None) -> str:
    """执行安全的 SQL（仅支持 SELECT，自动添加安全检查）
    
    Args:
        sql: SQL 语句（会自动验证安全性）
        db_path: 数据库文件路径（可选，默认使用演示数据库）
    
    Returns:
        执行结果
    """
    return query_data(sql, db_path)  # 复用 query_data 的安全检查


@mcp.tool()
def get_table_stats(table_name: str, db_path: str = None) -> str:
    """获取表的统计信息（行数、字段数等）
    
    Args:
        table_name: 表名
        db_path: 数据库文件路径（可选，默认使用演示数据库）
    
    Returns:
        表的统计信息
    """
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            conn.close()
            return f"❌ 表 '{table_name}' 不存在"
        
        # 行数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        # 字段数
        cursor.execute(f"PRAGMA table_info({table_name})")
        column_count = len(cursor.fetchall())
        
        conn.close()
        
        return f"""表 '{table_name}' 的统计信息:

📊 行数: {row_count}
📋 字段数: {column_count}
"""
    
    except Exception as e:
        return f"❌ 获取统计信息失败: {str(e)}"


if __name__ == "__main__":
    # 初始化演示数据库
    init_demo_db()
    
    # 启动 MCP Server（stdio 模式）
    print("🚀 SQLite MCP Server 启动（stdio 模式）", flush=True)
    mcp.run()
