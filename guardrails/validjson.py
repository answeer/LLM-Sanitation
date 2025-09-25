from openai import OpenAI
import os
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
client = OpenAI(
    api_key=DATABRICKS_TOKEN,
    base_url="https://xxxx/serving-endpoints"
)

response = client.chat.completions.create(
    model="databricks-claude-3-7-sonnet",
    messages=[
        {
            "role": "user",
            "content": "What is an LLM agent?"
        }
    ],
    max_tokens=5000
)

print(response.choices[0].message.content)
