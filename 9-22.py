#Code taken from dtsc discord
import openai 
from openai import OpenAI
import os


endpoint = "https://cdong1--azure-proxy-web-app.modal.run"
api_key = "supersecretkey"
deployment_name = "gpt-4o"
client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

response = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "developer",
            "content": "Talk like a princess."
        },
        {
            "role": "user",
            "content": "Are semicolons optional in JavaScript?"
        }
    ]
)

print(response.choices[0].message.content)