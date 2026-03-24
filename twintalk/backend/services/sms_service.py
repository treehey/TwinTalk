"""SMS sending service with provider abstraction.

By default, provider=mock which logs code to server logs for local development.
Set SMS_PROVIDER=twilio and required env vars to send real SMS.
"""

import os
import json
import base64
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


class SmsSendError(Exception):
    """Raised when SMS delivery fails."""


def send_verification_code(phone_number: str, code: str):
    provider = os.getenv("SMS_PROVIDER", "mock").strip().lower()

    if provider == "twilio":
        _send_via_twilio(phone_number, code)
        return {"provider": provider, "mock": False}

    if provider == "mock":
        logger.info("[MOCK_SMS] phone=%s code=%s", phone_number, code)
        return {"provider": provider, "mock": True}

    raise SmsSendError("未配置可用短信服务，请检查 SMS_PROVIDER")


def _send_via_twilio(phone_number: str, code: str):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    body_template = os.getenv(
        "SMS_BODY_TEMPLATE",
        "[TwinTalk] Your verification code is {code}. It expires in 5 minutes.",
    )

    if not account_sid or not auth_token or not from_number:
        raise SmsSendError("Twilio 配置不完整，请设置 TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_FROM_NUMBER")

    body = body_template.format(code=code)
    endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    payload = urlencode({"To": phone_number, "From": from_number, "Body": body}).encode("utf-8")

    token = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    req = Request(endpoint, data=payload, method="POST")
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urlopen(req, timeout=12) as res:
            raw = res.read().decode("utf-8")
        data = json.loads(raw)
        if data.get("error_code"):
            raise SmsSendError(data.get("message") or "短信服务返回错误")
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else str(e)
        raise SmsSendError(f"短信发送失败: HTTP {e.code} {detail}") from e
    except URLError as e:
        raise SmsSendError(f"短信发送失败: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise SmsSendError("短信服务响应解析失败") from e
