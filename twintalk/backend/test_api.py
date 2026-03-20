"""Quick sanity test for the Hunyuan API connection.

Usage:
    python test_api.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1")
model = os.getenv("OPENAI_MODEL", "hunyuan-lite")

if not api_key:
    print("ERROR: OPENAI_API_KEY not set. Please configure your .env file.")
    exit(1)

client = OpenAI(api_key=api_key, base_url=base_url)

try:
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "hi"}],
    )
    print("SUCCESS", r.choices[0].message.content)
except Exception as e:
    print("ERROR", type(e), str(e))
