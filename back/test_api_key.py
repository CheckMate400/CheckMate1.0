import openai
from dotenv import load_dotenv
import os

# Load .env file if you're using one
load_dotenv()

# Optional: manually set the key here if not using .env
# openai.api_key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxx"

try:
    client = openai.OpenAI()

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Summarize this: Physics exams are hard."}
        ],
        max_tokens=100
    )

    print("✅ API key is working!")
    print("💬 Response summary:\n", response.choices[0].message.content)

except Exception as e:
    print("❌ Failed to connect to OpenAI API:")
    print(e)
