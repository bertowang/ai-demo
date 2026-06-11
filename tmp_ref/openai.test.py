from openai import OpenAI

client = OpenAI(
  api_key="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"
)

response = client.responses.create(
  model="gpt-5.4-mini",
  input="write a haiku about ai",
  store=True,
)

print(response.output_text);
