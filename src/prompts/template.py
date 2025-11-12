# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import dataclasses
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState

from src.config.configuration import Configuration

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def get_prompt_template(prompt_name: str, locale: str = "en-US") -> str:
    """
    Load and return a prompt template using Jinja2 with locale support.

    Args:
        prompt_name: Name of the prompt template file (without .md extension)
        locale: Language locale (e.g., en-US, zh-CN). Defaults to en-US

    Returns:
        The template string with proper variable substitution syntax
    """
    try:
        # Normalize locale format
        normalized_locale = locale.replace("-", "_") if locale and locale.strip() else "en_US"
        
        # Try locale-specific template first (e.g., researcher.zh_CN.md)
        try:
            template = env.get_template(f"{prompt_name}.{normalized_locale}.md")
            return template.render()
        except TemplateNotFound:
            # Fallback to English template if locale-specific not found
            template = env.get_template(f"{prompt_name}.md")
            return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name} for locale {locale}: {e}")


def apply_prompt_template(
    prompt_name: str, state: AgentState, configurable: Configuration = None, locale: str = "en-US"
) -> list:
    """
    Apply template variables to a prompt template and return formatted messages.

    Args:
        prompt_name: Name of the prompt template to use
        state: Current agent state containing variables to substitute
        configurable: Configuration object with additional variables
        locale: Language locale for template selection (e.g., en-US, zh-CN)

    Returns:
        List of messages with the system prompt as the first message
    """
    # ============================================================
    # 1. 상태 변수 준비
    # - state를 딕셔너리로 변환하여 템플릿 렌더링에 사용
    # - CURRENT_TIME: 현재 시간을 템플릿 변수로 추가
    # - state의 모든 값을 템플릿 변수로 사용 가능하게 함
    # ============================================================
    state_vars = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        **state,
    }

    # ============================================================
    # 2. 추가 설정 변수 병합
    # - Configuration 객체의 값들을 템플릿 변수에 추가
    # - resources, max_search_results 등의 설정값 포함
    # ============================================================
    if configurable:
        state_vars.update(dataclasses.asdict(configurable))

    try:
        # ============================================================
        # 3. Locale 정규화 및 템플릿 로드
        # - Locale 형식 정규화 (en-US → en_US)
        # - 다국어 지원: 해당 Locale의 템플릿 우선 시도
        # - 폴백: Locale 템플릿이 없으면 영어 템플릿 사용
        # ============================================================
        # Locale 형식 정규화 (하이픈을 언더스코어로 변환)
        normalized_locale = locale.replace("-", "_") if locale and locale.strip() else "en_US"
        
        # Locale별 템플릿 로드 시도
        try:
            # 예: coordinator.ko_KR.md, planner.zh_CN.md
            template = env.get_template(f"{prompt_name}.{normalized_locale}.md")
        except TemplateNotFound:
            # Locale 템플릿이 없으면 기본 영어 템플릿 사용
            # 예: coordinator.md, planner.md
            template = env.get_template(f"{prompt_name}.md")
        
        # ============================================================
        # 4. 템플릿 렌더링 및 메시지 구성
        # - Jinja2 템플릿에 state_vars를 적용하여 렌더링
        # - 시스템 프롬프트를 첫 번째 메시지로 추가
        # - 기존 대화 메시지들을 그 다음에 연결
        # ============================================================
        system_prompt = template.render(**state_vars)
        return [{"role": "system", "content": system_prompt}] + state["messages"]
    except Exception as e:
        raise ValueError(f"Error applying template {prompt_name} for locale {locale}: {e}")
