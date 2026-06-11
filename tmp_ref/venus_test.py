#!/usr/bin/env python3
"""
Venus 平台 API 简单访问测试

参考 openai.test.py 的做法，使用腾讯内部 Venus 平台 LLM 代理服务
文档：https://iwiki.woa.com/p/4009937875

使用方法：
    python venus_test.py
"""

from openai import OpenAI


def main() -> None:
    """
    主函数：测试 Venus 平台 API 访问
    """
    # ============================================================
    # Venus 平台配置
    # ============================================================
    url: str = "http://v2.open.venus.oa.com/llmproxy"
    token: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
    
    # ============================================================
    # 创建 OpenAI 客户端（指向 Venus 平台）
    # ============================================================
    client = OpenAI(
        api_key=token,
        base_url=url,
    )
    
    print("=" * 60)
    print("Venus 平台 API 访问测试")
    print("=" * 60)
    print(f"\n📡 URL: {url}")
    print(f"🔑 Token: {token[:20]}...")
    print(f"🤖 Model: gpt-4o-mini\n")
    print("-" * 60)
    
    # ============================================================
    # 测试 1：简单对话
    # ============================================================
    print("\n【测试 1】简单对话测试\n")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一个有帮助的助手。"},
                {"role": "user", "content": "请用一句话介绍什么是 Agent？"}
            ],
            max_tokens=100,
            temperature=0.7,
        )
        
        answer: str = response.choices[0].message.content
        print(f"✅ 成功！")
        print(f"📝 回答：{answer}")
        print(f"📊 Token 使用：{response.usage.total_tokens}")
        
    except Exception as e:
        print(f"❌ 失败：{str(e)}")
    
    print("\n" + "-" * 60)
    
    # ============================================================
    # 测试 2：工具调用（Function Calling）
    # ============================================================
    print("\n【测试 2】工具调用测试\n")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "北京今天天气怎么样？"}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称，如：北京、上海"
                            }
                        },
                        "required": ["city"]
                    }
                }
            }],
            tool_choice="auto",
        )
        
        message = response.choices[0].message
        
        # 检查是否有工具调用
        if message.tool_calls:
            print(f"✅ 成功！LLM 请求调用工具")
            for tool_call in message.tool_calls:
                print(f"🔧 工具名称：{tool_call.function.name}")
                print(f"📝 参数：{tool_call.function.arguments}")
        else:
            print(f"✅ 成功！直接回答")
            print(f"📝 回答：{message.content}")
        
        print(f"📊 Token 使用：{response.usage.total_tokens}")
        
    except Exception as e:
        print(f"❌ 失败：{str(e)}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
