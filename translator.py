"""번역 로직 모듈."""

import json
import os

import openai
import streamlit as st
from dotenv import load_dotenv

DEFAULT_MODEL = "gpt-6-astra"
MAX_CHARS = 5000

# 결과 키 -> 화면에 표시할 언어 이름. 언어를 추가하려면 여기에만 추가한다.
TARGET_LANGUAGES = {
    "english": "English",
    "japanese": "日本語",
    "spanish": "Español",
}

SYSTEM_PROMPT = (
    "너는 전문 번역가다. 사용자가 준 글의 원문 언어를 스스로 파악하고, "
    "원문의 의미, 어조, 줄바꿈을 유지하면서 다음 언어로 자연스럽게 번역하라: "
    + ", ".join(TARGET_LANGUAGES.values())
    + ". 결과는 "
    + ", ".join(TARGET_LANGUAGES.keys())
    + " 키를 가진 JSON 객체로만 답하라."
)


class TranslationError(Exception):
    """사용자에게 보여줄 한국어 메시지를 담은 번역 오류."""


def _get_secret(key: str):
    """st.secrets에서 값을 읽는다. secrets 파일이 없으면 None을 반환한다."""
    try:
        return st.secrets.get(key)
    except Exception:
        return None


def load_config() -> dict:
    """설정값을 읽는다. st.secrets를 우선하고, 없으면 .env를 사용한다."""
    load_dotenv()
    api_key = _get_secret("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = _get_secret("OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
    password = _get_secret("APP_PASSWORD") or os.getenv("APP_PASSWORD")
    return {"api_key": api_key, "model": model, "password": password}


def _parse_result(content: str) -> dict:
    """모델 응답(JSON 문자열)을 언어별 결과 dict로 바꾼다."""
    try:
        data = json.loads(content or "")
    except json.JSONDecodeError:
        raise TranslationError("번역 결과를 처리하지 못했습니다. 다시 시도해 주세요.")
    if not isinstance(data, dict) or not all(
        isinstance(data.get(key), str) for key in TARGET_LANGUAGES
    ):
        raise TranslationError("번역 결과를 처리하지 못했습니다. 다시 시도해 주세요.")
    return {key: data[key] for key in TARGET_LANGUAGES}


def translate(text: str) -> dict:
    """입력 글을 대상 언어로 번역한다. 실패하면 TranslationError를 발생시킨다."""
    config = load_config()
    if not config["api_key"]:
        raise TranslationError(
            "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요."
        )

    client = openai.OpenAI(api_key=config["api_key"])
    model = config["model"]
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
    except openai.AuthenticationError:
        raise TranslationError("API 키가 올바르지 않습니다.")
    except (openai.NotFoundError, openai.PermissionDeniedError):
        raise TranslationError(
            f"`{model}` 모델을 사용할 수 없습니다. 모델명과 계정 권한을 확인해 주세요."
        )
    except openai.RateLimitError:
        raise TranslationError("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    except (openai.APIConnectionError, openai.APIError):
        raise TranslationError("번역 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")

    return _parse_result(response.choices[0].message.content)
