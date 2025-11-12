# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import os
from pathlib import Path
from typing import Any, Dict, get_args

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from src.config import load_yaml_config
from src.config.agents import LLMType
from src.llms.providers.dashscope import ChatDashscope

# Cache for LLM instances
_llm_cache: dict[LLMType, BaseChatModel] = {}


def _get_config_file_path() -> str:
    """Get the path to the configuration file."""
    return str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())


def _get_llm_type_config_keys() -> dict[str, str]:
    """Get mapping of LLM types to their configuration keys."""
    return {
        "reasoning": "REASONING_MODEL",
        "basic": "BASIC_MODEL",
        "vision": "VISION_MODEL",
        "code": "CODE_MODEL",
    }


def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix) :].lower()
            conf[conf_key] = value
    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    """Create LLM instance using configuration."""
    # ============================================================
    # 1. LLM 설정 키 가져오기 및 검증
    # - llm_type에 해당하는 설정 키를 조회
    # - 설정 파일(config.yaml)에서 해당 LLM의 설정을 추출
    # ============================================================
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)

    if not config_key:
        raise ValueError(f"Unknown LLM type: {llm_type}")

    llm_conf = conf.get(config_key, {})
    if not isinstance(llm_conf, dict):
        raise ValueError(f"Invalid LLM configuration for {llm_type}: {llm_conf}")

    # ============================================================
    # 2. 환경 변수 설정 병합
    # - 환경 변수에서 LLM 설정을 가져옴
    # - 파일 설정과 환경 변수 설정을 병합 (환경 변수가 우선)
    # - 불필요한 파라미터 제거 (token_limit 등)
    # ============================================================
    env_conf = _get_env_llm_conf(llm_type)

    # 설정 병합: 환경 변수가 우선순위를 가짐
    merged_conf = {**llm_conf, **env_conf}

    # 클라이언트 초기화 시 불필요한 파라미터 제거
    if "token_limit" in merged_conf:
        merged_conf.pop("token_limit")

    if not merged_conf:
        raise ValueError(f"No configuration found for LLM type: {llm_type}")

    # ============================================================
    # 3. 재시도 및 SSL 검증 설정
    # - max_retries: Rate limit 오류 처리를 위한 재시도 횟수 설정
    # - SSL 검증 비활성화 시 커스텀 HTTP 클라이언트 생성
    # ============================================================
    # Rate limit 오류 처리를 위한 재시도 설정 추가
    if "max_retries" not in merged_conf:
        merged_conf["max_retries"] = 3

    # SSL 검증 설정 처리
    verify_ssl = merged_conf.pop("verify_ssl", True)

    # SSL 검증이 비활성화된 경우 커스텀 HTTP 클라이언트 생성
    if not verify_ssl:
        http_client = httpx.Client(verify=False)
        http_async_client = httpx.AsyncClient(verify=False)
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client

    # ============================================================
    # 4. 플랫폼별 LLM 인스턴스 생성 - Google AI Studio
    # - Google AI Studio (Gemini) 플랫폼 감지
    # - Google 특화 설정으로 변환 (api_key → google_api_key)
    # - Google AI Studio에서 지원하지 않는 파라미터 제거
    # ============================================================
    platform = merged_conf.get("platform", "").lower()
    is_google_aistudio = platform == "google_aistudio" or platform == "google-aistudio"

    if is_google_aistudio:
        # Google AI Studio 전용 설정 처리
        gemini_conf = merged_conf.copy()

        # 공통 키를 Google AI Studio 전용 키로 매핑
        if "api_key" in gemini_conf:
            gemini_conf["google_api_key"] = gemini_conf.pop("api_key")

        # Google AI Studio에서 사용하지 않는 파라미터 제거
        gemini_conf.pop("base_url", None)
        gemini_conf.pop("platform", None)

        # Google AI Studio에서 지원하지 않는 파라미터 제거
        gemini_conf.pop("http_client", None)
        gemini_conf.pop("http_async_client", None)

        return ChatGoogleGenerativeAI(**gemini_conf)

    # ============================================================
    # 5. 플랫폼별 LLM 인스턴스 생성 - Azure OpenAI
    # - Azure 엔드포인트 감지 시 AzureChatOpenAI 반환
    # ============================================================
    if "azure_endpoint" in merged_conf or os.getenv("AZURE_OPENAI_ENDPOINT"):
        return AzureChatOpenAI(**merged_conf)

    # ============================================================
    # 6. 플랫폼별 LLM 인스턴스 생성 - Dashscope (Alibaba Cloud)
    # - base_url에서 dashscope 감지
    # - reasoning 타입일 경우 thinking 기능 활성화
    # ============================================================
    if "base_url" in merged_conf and "dashscope." in merged_conf["base_url"]:
        if llm_type == "reasoning":
            merged_conf["extra_body"] = {"enable_thinking": True}
        else:
            merged_conf["extra_body"] = {"enable_thinking": False}
        return ChatDashscope(**merged_conf)

    # ============================================================
    # 7. 플랫폼별 LLM 인스턴스 생성 - DeepSeek 및 기본 OpenAI
    # - reasoning 타입: DeepSeek 사용 (추론 특화 모델)
    # - 기타: 표준 OpenAI API 호환 모델 사용
    # ============================================================
    if llm_type == "reasoning":
        # DeepSeek는 base_url 대신 api_base 파라미터 사용
        merged_conf["api_base"] = merged_conf.pop("base_url", None)
        return ChatDeepSeek(**merged_conf)
    else:
        # 기본: OpenAI 호환 클라이언트 반환
        return ChatOpenAI(**merged_conf)


def get_llm_by_type(llm_type: LLMType) -> BaseChatModel:
    """
    Get LLM instance by type. Returns cached instance if available.
    """
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]

    conf = load_yaml_config(_get_config_file_path())
    llm = _create_llm_use_conf(llm_type, conf)
    _llm_cache[llm_type] = llm
    return llm


def get_configured_llm_models() -> dict[str, list[str]]:
    """
    Get all configured LLM models grouped by type.

    Returns:
        Dictionary mapping LLM type to list of configured model names.
    """
    try:
        conf = load_yaml_config(_get_config_file_path())
        llm_type_config_keys = _get_llm_type_config_keys()

        configured_models: dict[str, list[str]] = {}

        for llm_type in get_args(LLMType):
            # Get configuration from YAML file
            config_key = llm_type_config_keys.get(llm_type, "")
            yaml_conf = conf.get(config_key, {}) if config_key else {}

            # Get configuration from environment variables
            env_conf = _get_env_llm_conf(llm_type)

            # Merge configurations, with environment variables taking precedence
            merged_conf = {**yaml_conf, **env_conf}

            # Check if model is configured
            model_name = merged_conf.get("model")
            if model_name:
                configured_models.setdefault(llm_type, []).append(model_name)

        return configured_models

    except Exception as e:
        # Log error and return empty dict to avoid breaking the application
        print(f"Warning: Failed to load LLM configuration: {e}")
        return {}


def get_llm_token_limit_by_type(llm_type: str) -> int:
    """
    Get the maximum token limit for a given LLM type.

    Args:
        llm_type (str): The type of LLM.

    Returns:
        int: The maximum token limit for the specified LLM type.
    """

    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)

    conf = load_yaml_config(_get_config_file_path())
    llm_max_token = conf.get(config_key, {}).get("token_limit")
    return llm_max_token


# In the future, we will use reasoning_llm and vl_llm for different purposes
# reasoning_llm = get_llm_by_type("reasoning")
# vl_llm = get_llm_by_type("vision")
