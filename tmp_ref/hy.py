import os
from openai import OpenAI

# Venus 平台配置
url = "http://v2.open.venus.oa.com/llmproxy"
token = "teWS8OdeWJ4dfaVBTGjkbTje@4186"

# 创建 OpenAI 客户端（指向 Venus 平台）
client = OpenAI(
    api_key=token,
    base_url=url,
)

response = client.chat.completions.create(
  model="gpt-4o-mini",
  messages=[
    {"role": "user", "content": "你好！你是谁啊"}
  ]
)
print(response.choices[0].message.content)