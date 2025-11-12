# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Optional, Union

from pydantic import BaseModel, Field

from src.config.report_style import ReportStyle
from src.rag.retriever import Resource


class ContentItem(BaseModel):
    # 한국어: 콘텐츠 타입 (text, image 등)
    type: str = Field(..., description="The type of content (text, image, etc.)")
    # 한국어: 텍스트 콘텐츠 (type이 'text'인 경우)
    text: Optional[str] = Field(None, description="The text content if type is 'text'")
    # 한국어: 이미지 URL (type이 'image'인 경우)
    image_url: Optional[str] = Field(
        None, description="The image URL if type is 'image'"
    )


class ChatMessage(BaseModel):
    # 한국어: 메시지 발신자 역할 (user 또는 assistant)
    role: str = Field(
        ..., description="The role of the message sender (user or assistant)"
    )
    # 한국어: 메시지 콘텐츠 (문자열 또는 ContentItem 리스트)
    content: Union[str, List[ContentItem]] = Field(
        ...,
        description="The content of the message, either a string or a list of content items",
    )


class ChatRequest(BaseModel):
    # 한국어: 사용자와 어시스턴트 간의 메시지 기록
    messages: Optional[List[ChatMessage]] = Field(
        [], description="History of messages between the user and the assistant" 
    )
    # 한국어: 연구에 사용될 리소스
    resources: Optional[List[Resource]] = Field(
        [], description="Resources to be used for the research" 
    )
    # 한국어: 디버그 로깅 활성화 여부
    debug: Optional[bool] = Field(False, description="Whether to enable debug logging") 
    # 한국어: 특정 대화 식별자 (기본값: __default__)
    thread_id: Optional[str] = Field(
        "__default__", description="A specific conversation identifier" 
    )
    # 한국어: 대화에 사용될 언어 로케일 (기본값: en-US)
    locale: Optional[str] = Field(
        "en-US", description="Language locale for the conversation (default: en-US)" 
    )
    # 한국어: 최대 계획 반복 횟수 (기본값: 1)
    max_plan_iterations: Optional[int] = Field(
        1, description="The maximum number of plan iterations" 
    )
    # 한국어: 계획에 사용될 최대 단계 수 (기본값: 3)    
    max_step_num: Optional[int] = Field(
        3, description="The maximum number of steps in a plan"
    )
    # 한국어: 최대 검색 결과 수 (기본값: 3)
    max_search_results: Optional[int] = Field(
        3, description="The maximum number of search results" 
    )
    # 한국어: 계획을 자동으로 수락할지 여부 (기본값: False)
    auto_accepted_plan: Optional[bool] = Field(
        False, description="Whether to automatically accept the plan" 
    )
    # 한국어: 계획에 대한 사용자 인터럽트 피드백 (기본값: None)
    interrupt_feedback: Optional[str] = Field(
        None, description="Interrupt feedback from the user on the plan" 
    )
    # 한국어: 채팅 요청에 대한 MCP 설정 (기본값: None)
    mcp_settings: Optional[dict] = Field(
        None, description="MCP settings for the chat request" 
    )
    # 한국어: 계획 전에 배경 조사를 수행할지 여부 (기본값: True)
    enable_background_investigation: Optional[bool] = Field(
        True, description="Whether to get background investigation before plan" 
    )
    # 한국어: 보고서 스타일 (기본값: ACADEMIC)
    report_style: Optional[ReportStyle] = Field(
        ReportStyle.ACADEMIC, description="The style of the report" 
    )
    # 한국어: 심층 사고를 활성화할지 여부 (기본값: False)
    enable_deep_thinking: Optional[bool] = Field(
        False, description="Whether to enable deep thinking" 
    )
    # 한국어: 다중 턴 명확화를 활성화할지 여부 (기본값: None, State 기본값: False)
    enable_clarification: Optional[bool] = Field(
        None,
        description="Whether to enable multi-turn clarification (default: None, uses State default=False)",
    )
    # 한국어: 최대 명확화 라운드 수 (기본값: None, State 기본값: 3)
    max_clarification_rounds: Optional[int] = Field(
        None,
        description="Maximum number of clarification rounds (default: None, uses State default=3)",
    )
    # 한국어: 실행 전에 인터럽트할 도구 이름 목록 (기본값: [])
    interrupt_before_tools: List[str] = Field(
        default_factory=list,
        description="List of tool names to interrupt before execution (e.g., ['db_tool', 'api_tool'])",
    )


class TTSRequest(BaseModel):
    text: str = Field(..., description="The text to convert to speech")
    voice_type: Optional[str] = Field(
        "BV700_V2_streaming", description="The voice type to use"
    )
    encoding: Optional[str] = Field("mp3", description="The audio encoding format")
    speed_ratio: Optional[float] = Field(1.0, description="Speech speed ratio")
    volume_ratio: Optional[float] = Field(1.0, description="Speech volume ratio")
    pitch_ratio: Optional[float] = Field(1.0, description="Speech pitch ratio")
    text_type: Optional[str] = Field("plain", description="Text type (plain or ssml)")
    with_frontend: Optional[int] = Field(
        1, description="Whether to use frontend processing"
    )
    frontend_type: Optional[str] = Field("unitTson", description="Frontend type")


class GeneratePodcastRequest(BaseModel):
    content: str = Field(..., description="The content of the podcast")


class GeneratePPTRequest(BaseModel):
    content: str = Field(..., description="The content of the ppt")


class GenerateProseRequest(BaseModel):
    prompt: str = Field(..., description="The content of the prose")
    option: str = Field(..., description="The option of the prose writer")
    command: Optional[str] = Field(
        "", description="The user custom command of the prose writer"
    )


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(..., description="The original prompt to enhance")
    context: Optional[str] = Field(
        "", description="Additional context about the intended use"
    )
    report_style: Optional[str] = Field(
        "academic", description="The style of the report"
    )
