"""LLM Client — unified interface to call OpenAI-compatible APIs."""

import json
import logging
import os
import re
import queue
import threading
from typing import Generator, Optional

from openai import OpenAI
import openai

logger = logging.getLogger(__name__)

class APIKeyPool:
    def __init__(self, keys_str: Optional[str] = None):
        if keys_str is None:
            # 优先读取 OPENAI_API_KEYS (逗号分隔)，如果不存在则兼容 OPENAI_API_KEY
            keys_str = os.getenv("OPENAI_API_KEYS", os.getenv("OPENAI_API_KEY", ""))
        
        raw_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        
        # 过滤无效 Key
        invalid_values = {
            "your-hunyuan-api-key-here",
            "sk-your-api-key-here",
            "your_openai_api_key_here",
        }
        self.keys = [k for k in raw_keys if k not in invalid_values and not k.startswith("AKID")]
        
        self.pool = queue.Queue()
        
        if not self.keys:
            logger.warning("[APIKeyPool] No API keys provided. Offline mode will be used.")
            # 放入一个空字符串作为离线模式占位符
            self.pool.put("")
        else:
            for key in self.keys:
                self.pool.put(key)
            logger.info(f"[APIKeyPool] Initialized with {len(self.keys)} keys.")

    def get(self, timeout: Optional[float] = 10.0) -> str:
        try:
            key = self.pool.get(timeout=timeout)
            if key:
                logger.info(f"[APIKeyPool] 成功借出 Key({key[:10]}...)")
            return key
        except queue.Empty:
            logger.warning("[APIKeyPool] 等待空闲 Key 超时，当前系统繁忙，所有 Key 均被借出或在冷却中。")
            raise

    def put(self, key: str):
        self.pool.put(key)
        if key:
            logger.debug(f"[APIKeyPool] 成功归还 Key({key[:10]}...)")

    def cooldown(self, key: str, cooldown_seconds: int = 20):
        if key:
            logger.warning(f"[APIKeyPool] Key({key[:10]}...) 触发限流，进入冷却 {cooldown_seconds}s")
            
        def _return_key():
            self.put(key)
            if key:
                logger.info(f"[APIKeyPool] Key({key[:10]}...) 冷却结束，重新加入空闲池")
                
        timer = threading.Timer(cooldown_seconds, _return_key)
        timer.daemon = True
        timer.start()

# 全局单例
_api_key_pool: Optional[APIKeyPool] = None

def get_api_key_pool() -> APIKeyPool:
    global _api_key_pool
    if _api_key_pool is None:
        _api_key_pool = APIKeyPool()
    return _api_key_pool

_client_cache = {}

def get_client_for_key(api_key: str) -> OpenAI:
    """为特定的 API Key 获取或创建 OpenAI 客户端"""
    if not api_key:
        # 当使用空字符串意味着处于离线模拟模式时，随便给个客户端占位置，尽管不会真调
        return OpenAI(api_key="mock", base_url="mock")
        
    if api_key not in _client_cache:
        _client_cache[api_key] = OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    return _client_cache[api_key]


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def call_llm_with_pool(prompt: str, max_retries: int = 3, **kwargs) -> str:
    """
    通过线程池管理调用 LLM。自带限流处理和重试机制。
    允许通过 kwargs 传递额外的调用参数 (例如 system_prompt, history, temperature 等)。
    """
    pool = get_api_key_pool()
    
    for attempt in range(max_retries):
        try:
            key = pool.get(timeout=10.0)
        except queue.Empty:
            return "系统繁忙：当前所有连接均在被使用或冷却中，请稍后再试。"
            
        if not key:
            pool.put(key)
            return "【离线模拟】未配置有效的 OPENAI_API_KEYS。此为离线状态下的占位回复。"
            
        client = get_client_for_key(key)
        
        # 封装 messages 参数
        system_prompt = kwargs.get("system_prompt", "你是一个有用的助手。")
        messages = [{"role": "system", "content": system_prompt}]
        if kwargs.get("history"):
            messages.extend(kwargs.get("history"))
        messages.append({"role": "user", "content": prompt})

        # 安全限制已移除，直接请求并放行
        try:
            response = client.chat.completions.create(
                model=get_model(),
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
            )
            pool.put(key) # 成功后归还 Key
            return response.choices[0].message.content
            
        except openai.RateLimitError:
            # 429 Too Many Requests -> 冷却
            pool.cooldown(key, cooldown_seconds=20)
            logger.warning(f"[APIKeyPool] Attempt {attempt + 1}: RateLimitError logic triggered, retrying...")
            continue
            
        except Exception as e:
            # 其他网络或 API 错误
            pool.put(key)
            logger.error(f"[APIKeyPool] Attempt {attempt + 1}: Network or API error occurred: {e}")
            if attempt == max_retries - 1:
                return "LLM 请求彻底失败：" + str(e)
            continue
            
    return "已达到最大重试次数，LLM 请求失败。"


def _extract_json_object(content: str) -> Optional[dict]:
    """Best-effort extraction for providers that do not support response_format."""
    if not content:
        return None

    text = content.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            data, _ = decoder.raw_decode(text[index:])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    return None


def call_llm(
    system_prompt: str,
    user_message: str,
    history: list = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> str:
    """Call the LLM and return the full response text."""
    return call_llm_with_pool(
        prompt=user_message,
        system_prompt=system_prompt,
        history=history,
        temperature=temperature,
        max_tokens=max_tokens
    )


def call_llm_stream(
    system_prompt: str,
    user_message: str,
    history: list = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> Generator[str, None, None]:
    """Call the LLM and yield response chunks (SSE)."""
    pool = get_api_key_pool()
    try:
        key = pool.get(timeout=5.0)
    except queue.Empty:
        yield "系统繁忙：当前所有连接均在被使用或冷却中，请稍后再试。"
        return

    if not key:
        pool.put(key)
        yield "【离线模拟】未配置 OPENAI_API_KEY。此为离线状态下的占位回复。"
        return

    client = get_client_for_key(key)
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        stream = client.chat.completions.create(
            model=get_model(),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        pool.put(key)
    except openai.RateLimitError:
        pool.cooldown(key, cooldown_seconds=20)
        yield "\n[系统提示] 请求触发限流，请稍后重试。"
    except Exception as e:
        pool.put(key)
        logger.error(f"LLM stream call failed: {e}")
        yield f"\n[系统提示] 请求发生错误: {e}"


def call_llm_json(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> Optional[dict]:
    """Call the LLM expecting a JSON response. Returns parsed dict or None."""
    pool = get_api_key_pool()
    try:
        key = pool.get(timeout=10.0)
    except queue.Empty:
        logger.warning("[APIKeyPool] call_llm_json failed due to queue Empty")
        return None

    if not key:
        pool.put(key)
        return {
            "questions": [
                {
                    "id": "mock_q_1",
                    "title": "(离线模拟) 这是系统默认问题选项A还是选项B？",
                    "options": ["A", "B", "C"]
                }
            ]
        }

    client = get_client_for_key(key)
    messages = [
        {
            "role": "system",
            "content": "你是一个结构化数据生成助手。请严格按照要求输出 JSON 格式，不要包含任何其他文本。",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        try:
            response = client.chat.completions.create(
                model=get_model(),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            logger.warning(
                "Structured JSON response_format unavailable for model %s, falling back to text parsing: %s",
                get_model(),
                exc,
            )
            fallback_messages = [
                {
                    "role": "system",
                    "content": (
                        "你是一个结构化数据生成助手。"
                        "请只输出一个合法 JSON 对象，不要输出 Markdown、解释、前后缀文本。"
                    ),
                },
                {"role": "user", "content": prompt},
            ]
            response = client.chat.completions.create(
                model=get_model(),
                messages=fallback_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        pool.put(key)
        content = response.choices[0].message.content or ""
        parsed = _extract_json_object(content)
        if parsed is None:
            logger.error("Failed to extract JSON object from LLM response: %s", content)
        return parsed
    except openai.RateLimitError:
        pool.cooldown(key, cooldown_seconds=20)
        logger.error("LLM JSON call RateLimitError")
        return None
    except json.JSONDecodeError as e:
        pool.put(key)
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None
    except Exception as e:
        pool.put(key)
        logger.error(f"LLM JSON call failed: {e}")
        return None
