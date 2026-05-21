from __future__ import annotations

import logging
import os
import sys
from typing import Any

import requests


OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)


class OpenRouterCallError(RuntimeError):
    """Safe OpenRouter error that never contains API keys."""


def _streamlit_module() -> Any | None:
    if "streamlit" not in sys.modules:
        return None
    return sys.modules["streamlit"]


def _has_streamlit_context() -> bool:
    if _streamlit_module() is None:
        return False
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        return False
    return get_script_run_ctx() is not None


def _secret_from_streamlit() -> str | None:
    if not _has_streamlit_context():
        return None
    st = _streamlit_module()
    if st is None:
        return None
    try:
        value = st.secrets.get("OPENROUTER_API_KEY")
    except Exception:
        try:
            value = st.secrets["OPENROUTER_API_KEY"]
        except Exception:
            value = None
    if value:
        return str(value).strip()
    return None


def get_openrouter_api_key() -> str | None:
    """Read OpenRouter key from Streamlit secrets first, then env vars."""

    return _secret_from_streamlit() or os.getenv("OPENROUTER_API_KEY", "").strip() or None


def has_openrouter_api_key() -> bool:
    return bool(get_openrouter_api_key())


def _notify_warning(message: str) -> None:
    logger.warning(message)
    if not _has_streamlit_context():
        return
    st = _streamlit_module()
    if st is None:
        return
    try:
        st.warning(message)
    except Exception:
        pass


def _notify_error(message: str) -> None:
    logger.error(message)
    if not _has_streamlit_context():
        return
    st = _streamlit_module()
    if st is None:
        return
    try:
        st.error("현재 답변 생성에 실패했습니다.")
    except Exception:
        pass


def _safe_error_reason(error: Exception) -> str:
    if isinstance(error, OpenRouterCallError) and str(error):
        return str(error)
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code:
        return f"HTTP {status_code}"
    return error.__class__.__name__


def _call_openrouter_model(
    model: str,
    messages: list[dict[str, str]],
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "Jeonse Safe Contract MVP",
    }
    try:
        response = requests.post(
            OPENROUTER_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise OpenRouterCallError(_safe_error_reason(error)) from error

    try:
        data = response.json()
    except ValueError as error:
        raise OpenRouterCallError("invalid_json_response") from error

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise OpenRouterCallError("missing_message_content") from error

    if not isinstance(content, str) or not content.strip():
        raise OpenRouterCallError("empty_message_content")
    return content.strip()


def call_openrouter(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1000,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> str | None:
    """
    Nvidia OpenRouter 모델을 단일 메인 모델로 호출합니다.
    기존 호출부 호환을 위해 함수명은 유지합니다.
    """

    api_key = get_openrouter_api_key()
    if not api_key:
        logger.info("OPENROUTER_API_KEY is not configured; skipping LLM call.")
        return None

    try:
        return _call_openrouter_model(
            DEFAULT_OPENROUTER_MODEL,
            messages,
            api_key,
            temperature,
            max_tokens,
            timeout,
        )
    except OpenRouterCallError as error:
        _notify_error(f"OpenRouter 모델 호출 실패: {_safe_error_reason(error)}")
        return None
