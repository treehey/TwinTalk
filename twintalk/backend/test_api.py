from openai import OpenAI

client = OpenAI(
    api_key="sk-oY5pROhj2s68ycbIlCWsKWYkc3xdvoKp2Wukjuy2NtuRWmJb",
    base_url="https://api.hunyuan.cloud.tencent.com/v1",
)

try:
    r = client.chat.completions.create(
        model="hunyuan-lite",
        messages=[{"role": "user", "content": "hi"}],
    )
    print("SUCCESS", r.choices[0].message.content)
except Exception as e:
    print("ERROR", type(e), str(e))
