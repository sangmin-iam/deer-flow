# LangGraph 스트리밍 아키텍처 가이드

이 문서는 Deer Flow 프로젝트의 LangGraph 기반 스트리밍 아키텍처를 설명합니다.

## 목차

1. [전체 아키텍처 개요](#전체-아키텍처-개요)
2. [주요 컴포넌트](#주요-컴포넌트)
3. [데이터 흐름](#데이터-흐름)
4. [핵심 개념](#핵심-개념)
5. [코드 분석](#코드-분석)

---

## 전체 아키텍처 개요

```
[클라이언트] ←→ [FastAPI] ←→ [LangGraph] ←→ [AI Agents]
     ↓            ↓              ↓
  fetch()   StreamingResponse  astream()
     ↓            ↓              ↓
  SSE 수신   제너레이터 yield   이벤트 생성
```

### 핵심 흐름

1. **클라이언트**: 사용자가 질문 입력
2. **FastAPI**: SSE 스트림 시작
3. **LangGraph**: 노드 실행하며 이벤트 생성
4. **AI Agents**: 실시간으로 응답 생성
5. **클라이언트**: 한 글자씩 화면에 표시

---

## 주요 컴포넌트

### 1. 프론트엔드 (TypeScript)

#### `fetch-stream.ts` - SSE 스트림 처리

```typescript
export async function* fetchStream(
  url: string,
  init: RequestInit,
): AsyncIterable<StreamEvent> {
  const response = await fetch(url, {...});

  // 바이트 스트림 → 텍스트로 디코딩
  const reader = response.body
    ?.pipeThrough(new TextDecoderStream())
    .getReader();

  // 이벤트를 하나씩 yield
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // \n\n으로 구분된 이벤트 파싱
    yield parseEvent(chunk);
  }
}
```

**역할:**

- HTTP 응답 스트림을 읽어서
- SSE 이벤트로 파싱
- 비동기 제너레이터로 하나씩 반환

**사용:**

```typescript
for await (const event of fetchStream(url, init)) {
  // event: { event: "message_chunk", data: {...} }
  // 화면에 실시간 표시
}
```

---

### 2. 백엔드 (Python)

#### `chat_request.py` - 데이터 전송 객체 (DTO)

```python
class ChatRequest(BaseModel):
    messages: Optional[List[ChatMessage]] = []
    resources: Optional[List[Resource]] = []
    max_plan_iterations: Optional[int] = 1
    max_step_num: Optional[int] = 3
    locale: Optional[str] = "en-US"
    # ... 기타 설정
```

**역할:**

- API 요청/응답 데이터 구조 정의
- Pydantic으로 자동 유효성 검사
- 타입 힌트와 문서화 제공

---

#### `app.py` - FastAPI 엔드포인트

##### 주요 함수들

**1. `_astream_workflow_generator()` - 워크플로우 준비 및 실행**

```python
async def _astream_workflow_generator(
    messages: List[dict],
    thread_id: str,
    resources: List[Resource],
    max_plan_iterations: int,
    max_step_num: int,
    # ... 기타 파라미터
):
    # 1. 준비: 로깅 및 초기화
    safe_thread_id = sanitize_thread_id(thread_id)

    # 2. 초기 메시지 전송 (에코백)
    for message in messages:
        _process_initial_messages(message, thread_id)

    # 3. workflow_input 생성 (State 초기값)
    workflow_input = {
        "messages": messages,
        "plan_iterations": 0,
        "final_report": "",
        "current_plan": None,
        # ... State 필드들
    }

    # 4. workflow_config 생성 (실행 설정)
    workflow_config = {
        "thread_id": thread_id,
        "max_plan_iterations": max_plan_iterations,
        "max_step_num": max_step_num,
        # ... Config 필드들
    }

    # 5. LangGraph 실행
    async for event in _stream_graph_events(
        graph, workflow_input, workflow_config, thread_id
    ):
        yield event
```

**역할:**

- API 요청을 LangGraph 형식으로 변환
- State 초기값과 Config 설정
- 이벤트를 클라이언트로 스트리밍

---

**2. `_stream_graph_events()` - LangGraph 이벤트 어댑터**

```python
async def _stream_graph_events(
    graph_instance, workflow_input, workflow_config, thread_id
):
    """
    LangGraph 이벤트를 SSE 형식으로 변환하는 어댑터 함수
    """
    try:
        # LangGraph 실행 시작
        async for agent, _, event_data in graph_instance.astream(
            workflow_input,
            config=workflow_config,
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ):
            # 이벤트 타입 분기
            if isinstance(event_data, dict):
                # Dict = State 업데이트
                if "__interrupt__" in event_data:
                    yield _create_interrupt_event(thread_id, event_data)
                continue  # 일반 State 업데이트는 무시

            # Tuple = 메시지 청크
            message_chunk, message_metadata = cast(
                tuple[BaseMessage, dict[str, Any]], event_data
            )

            # SSE 이벤트로 변환하여 전송
            async for event in _process_message_chunk(
                message_chunk, message_metadata, thread_id, agent
            ):
                yield event

    except Exception as e:
        yield _make_event("error", {...})
```

**역할:**

- LangGraph의 원시 이벤트를 받아서
- SSE 형식으로 변환
- Dict vs Tuple 타입별 처리

---

**3. `StreamingResponse` - FastAPI 응답**

```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        _astream_workflow_generator(...),
        media_type="text/event-stream"
    )
```

**역할:**

- 제너레이터를 HTTP 스트림으로 변환
- 클라이언트로 실시간 전송
- SSE 프로토콜 사용

---

#### `builder.py` - LangGraph 구조 정의

```python
def _build_base_graph():
    builder = StateGraph(State)

    # 노드 추가
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("background_investigator", background_investigation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reporter", reporter_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("coder", coder_node)

    # 엣지 추가
    builder.add_edge(START, "coordinator")
    builder.add_edge("background_investigator", "planner")
    builder.add_conditional_edges(
        "research_team",
        continue_to_running_research_team,
        ["planner", "researcher", "coder"]
    )
    builder.add_edge("reporter", END)

    return builder
```

**그래프 구조:**

```
START
  ↓
coordinator
  ↓
background_investigator
  ↓
planner
  ↓
research_team
  ↓ (조건부 분기)
  ├→ researcher → research_team (루프)
  ├→ coder → research_team (루프)
  └→ planner (재계획)

reporter
  ↓
END
```

---

#### `nodes.py` - 노드 구현

```python
def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "coordinator", "__end__"]]:
    """코디네이터 노드"""

    # 1. Config에서 설정 읽기
    configurable = Configuration.from_runnable_config(config)

    # 2. State에서 데이터 읽기
    messages = state["messages"]
    locale = state.get("locale", "en-US")

    # 3. AI 호출 및 처리
    response = llm.invoke(messages)

    # 4. State 업데이트 및 다음 노드 지정
    return Command(
        update={
            "messages": messages + [response],
            "locale": locale,
            "goto": "background_investigator"
        },
        goto="background_investigator"
    )
```

**노드의 역할:**

- State 읽기 (messages, plan 등)
- Config 읽기 (max_iterations 등)
- AI 호출 또는 작업 수행
- State 업데이트
- 다음 노드 지정 (goto)

---

## 데이터 흐름

### 1. 요청부터 응답까지

```
[1. 클라이언트 요청]
POST /api/chat/stream
{
  "messages": [{"role": "user", "content": "파이썬이 뭐야?"}],
  "max_plan_iterations": 1,
  "locale": "ko-KR"
}

[2. FastAPI 수신]
↓ ChatRequest DTO로 파싱
↓ _astream_workflow_generator() 호출

[3. 워크플로우 준비]
↓ workflow_input 생성 (State 초기값)
{
  "messages": [...],
  "plan_iterations": 0,
  "locale": "ko-KR"
}
↓ workflow_config 생성 (실행 설정)
{
  "thread_id": "abc123",
  "max_plan_iterations": 1
}

[4. LangGraph 실행]
↓ graph.astream(workflow_input, config=workflow_config)
↓ 노드 실행: coordinator → background_investigator → planner

[5. 이벤트 생성]
↓ Dict 이벤트: State 업데이트 (내부용)
↓ Tuple 이벤트: 메시지 청크 (클라이언트용)
↓ _stream_graph_events()가 변환

[6. SSE 전송]
↓ StreamingResponse로 스트리밍
event: message_chunk
data: {"content": "파이썬은", "role": "assistant"}

event: message_chunk
data: {"content": " 프로그래밍", "role": "assistant"}

[7. 클라이언트 수신]
↓ fetch-stream.ts가 파싱
↓ 화면에 실시간 표시
```

---

### 2. 이벤트 타입별 처리

#### Dict 이벤트 (stream_mode="updates")

**용도:** 내부 State 업데이트

```python
# LangGraph에서 생성
event_data = {
    'planner': {
        'plan_iterations': 1,
        'current_plan': {...},
        'observations': []
    }
}

# _stream_graph_events 처리
if isinstance(event_data, dict):
    if "__interrupt__" in event_data:
        yield _create_interrupt_event(...)  # 전달
    else:
        continue  # 스킵 (전달 안 됨)
```

**특징:**

- 99% 내부용 (클라이언트로 안 감)
- 1% interrupt는 예외적으로 전달
- 노드 간 데이터 공유

---

#### Tuple 이벤트 (stream_mode="messages")

**용도:** 클라이언트 표시용

```python
# LangGraph에서 생성
event_data = (
    AIMessageChunk(content="안녕"),
    {"langgraph_node": "researcher", "langgraph_step": 3}
)

# _stream_graph_events 처리
message_chunk, metadata = cast(tuple[...], event_data)
async for event in _process_message_chunk(...):
    yield event  # 항상 전달
```

**종류:**

- `AIMessageChunk`: 실시간 텍스트
- `ToolMessage`: 도구 실행 결과
- `HumanMessage`: 사용자 메시지

**특징:**

- 100% 클라이언트로 전달
- 실시간 스트리밍
- 화면 표시용

---

## 핵심 개념

### 1. State vs Config

| 구분     | State                     | Config                    |
| -------- | ------------------------- | ------------------------- |
| **타입** | `State` (MessagesState)   | `RunnableConfig`          |
| **용도** | 워크플로우 진행 상태      | 워크플로우 설정           |
| **수정** | ✅ 가능 (노드가 업데이트) | ❌ 불가 (읽기 전용)       |
| **범위** | 노드 간 공유, 계속 변경   | 전체 워크플로우 고정      |
| **예시** | messages, plan_iterations | max_iterations, thread_id |

**State 예시:**

```python
state = {
    "messages": [...],         # 대화 내용 (계속 추가됨)
    "plan_iterations": 0,      # 반복 횟수 (증가함)
    "current_plan": None,      # 현재 플랜 (변경됨)
    "observations": []         # 관찰 결과 (누적됨)
}
```

**Config 예시:**

```python
config = {
    "configurable": {
        "thread_id": "abc123",        # 세션 ID (고정)
        "max_plan_iterations": 3,     # 최대 반복 (고정)
        "max_step_num": 5,            # 최대 스텝 (고정)
        "report_style": "academic"    # 보고서 스타일 (고정)
    }
}
```

---

### 2. 비동기 제너레이터 (async generator)

**일반 함수 vs 제너레이터:**

```python
# 일반 함수 - 한 번에 모든 값 반환
def get_numbers():
    return [1, 2, 3, 4, 5]

# 제너레이터 - 하나씩 반환
def get_numbers():
    yield 1
    yield 2
    yield 3
```

**비동기 제너레이터:**

```python
async def stream_data():
    for i in range(5):
        await asyncio.sleep(0.1)  # 비동기 작업
        yield i

# 사용
async for value in stream_data():
    print(value)  # 0, 1, 2, 3, 4 (0.1초 간격)
```

**왜 사용하나?**

- 메모리 효율: 모든 데이터를 메모리에 올리지 않음
- 실시간 처리: 데이터가 준비되는 즉시 전달
- 비동기 지원: 다른 작업과 동시 실행

---

### 3. SSE (Server-Sent Events)

**형식:**

```
event: message_chunk
data: {"content": "안녕", "role": "assistant"}

event: tool_call_result
data: {"tool": "search", "result": "..."}

```

**특징:**

- HTTP 연결을 유지하며 서버가 푸시
- `\n\n`으로 이벤트 구분
- `event:` 이벤트 타입
- `data:` JSON 데이터

---

### 4. 타입 관련

#### `cast()` - 타입 힌트

```python
from typing import cast

# 타입 체커에게만 알려줌 (런타임 영향 없음)
data = cast(tuple[int, str], some_value)

# 실제로 변환하지 않음!
num = cast(int, "123")  # 여전히 문자열
result = num + 1        # 런타임 에러!
```

**언제 사용?**

- 타입 체커가 타입을 추론 못할 때
- isinstance() 체크 후 타입 명시
- 외부 라이브러리의 복잡한 타입

---

#### Docstring - 문서화 문자열

```python
def my_function(param: str) -> int:
    """
    함수의 역할 설명

    Args:
        param: 파라미터 설명

    Returns:
        int: 반환값 설명

    Examples:
        >>> my_function("test")
        42
    """
    return 42

# 런타임에 접근 가능
print(my_function.__doc__)

# IDE에서 자동 표시
# help(my_function)
```

---

### 5. 보안 - sanitize

**로그 인젝션 공격 방지:**

```python
# 공격 시나리오
user_input = "test\n[ERROR] System hacked!"

# sanitize 없이 로그
logger.info(f"User input: {user_input}")
# 출력:
# User input: test
# [ERROR] System hacked!  ← 가짜 에러 로그!

# sanitize 적용
safe_input = sanitize_log_input(user_input)
logger.info(f"User input: {safe_input}")
# 출력:
# User input: test\n[ERROR] System hacked!  ← 안전
```

**변환:**

- `\n` → `\\n` (줄바꿈 이스케이프)
- `\r` → `\\r` (캐리지 리턴)
- `\t` → `\\t` (탭)

---

### 6. json.dumps() - 직렬화

```python
import json

data = {
    "name": "홍길동",
    "age": 30,
    "active": True
}

# JSON 문자열로 변환
json_str = json.dumps(
    data,
    ensure_ascii=False,  # 유니코드 그대로
    separators=(",", ":")  # 공백 제거
)

# 결과: '{"name":"홍길동","age":30,"active":true}'
```

**파라미터:**

- `ensure_ascii=False`: 한글을 `\uXXXX`로 변환 안 함
- `separators=(",", ":")`: 공백 제거하여 크기 최소화

---

## 코드 분석

### `_stream_graph_events` 함수 상세

```python
async def _stream_graph_events(
    graph_instance, workflow_input, workflow_config, thread_id
):
    """
    LangGraph 이벤트를 SSE 형식으로 변환하는 어댑터 함수

    역할:
    - LangGraph의 원시 이벤트 스트림을 받아서
    - 클라이언트가 이해할 수 있는 SSE 이벤트로 변환
    - interrupt, 메시지 청크, 에러 등을 처리
    """
    # ========================================
    # 1. 준비 단계
    # ========================================
    safe_thread_id = sanitize_thread_id(thread_id)
    logger.debug(f"Starting graph event stream")

    try:
        event_count = 0

        # ========================================
        # 2. LangGraph 실행
        # ========================================
        async for agent, _, event_data in graph_instance.astream(
            workflow_input,           # State 초기값
            config=workflow_config,   # 실행 설정
            stream_mode=["messages", "updates"],  # 두 타입
            subgraphs=True,           # 서브그래프 포함
        ):
            event_count += 1

            # ========================================
            # 3. 이벤트 타입 분기
            # ========================================

            # 📌 분기 1: Dict = State 업데이트
            if isinstance(event_data, dict):
                # Interrupt 이벤트만 처리
                if "__interrupt__" in event_data:
                    yield _create_interrupt_event(thread_id, event_data)

                # 일반 State 업데이트는 무시
                continue

            # 📌 분기 2: Tuple = 메시지 청크
            message_chunk, metadata = cast(
                tuple[BaseMessage, dict], event_data
            )

            # ========================================
            # 4. SSE 이벤트로 변환
            # ========================================
            async for event in _process_message_chunk(
                message_chunk, metadata, thread_id, agent
            ):
                yield event  # 클라이언트로 전송

        logger.debug(f"Completed. Total events: {event_count}")

    # ========================================
    # 5. 에러 처리
    # ========================================
    except Exception as e:
        logger.exception("Error during graph execution")
        yield _make_event("error", {...})
```

---

### 분기 처리 상세

#### Dict 이벤트 처리

```python
if isinstance(event_data, dict):
    # Interrupt 체크
    if "__interrupt__" in event_data:
        # Interrupt 이벤트 생성
        yield _create_interrupt_event(thread_id, event_data)

        # 클라이언트는 이를 받아:
        # - "플랜 검토" 버튼 표시
        # - 사용자 승인 대기

    # Interrupt 아니면 스킵
    continue  # ← 다음 for 루프로
```

**continue 동작:**

```
async for event in astream():  ← continue가 여기로!
    ↓
    if dict:
        continue  ← 실행
    ↓
    (아래 코드는 실행 안 됨)
    message_chunk = ...
```

---

#### Tuple 이벤트 처리

```python
# Dict가 아니면 Tuple
message_chunk, metadata = cast(tuple[...], event_data)

# metadata 예시
{
    "langgraph_node": "researcher",  # 어느 노드
    "langgraph_step": 3              # 몇 번째 스텝
}

# message_chunk 타입별 처리
if isinstance(message_chunk, AIMessageChunk):
    # 실시간 텍스트 청크
    yield {
        "event": "message_chunk",
        "data": {
            "content": message_chunk.content,
            "role": "assistant",
            "agent": "researcher"
        }
    }

elif isinstance(message_chunk, ToolMessage):
    # 도구 실행 결과
    yield {
        "event": "tool_call_result",
        "data": {
            "tool": "search",
            "result": message_chunk.content
        }
    }
```

---

## 디버깅 팁

### 1. 이벤트 타입 확인

```python
# Dict vs Tuple 구분
print(f"Type: {type(event_data)}")
print(f"Is dict: {isinstance(event_data, dict)}")
print(f"Content: {event_data}")
```

### 2. State 확인

```python
def my_node(state: State, config: RunnableConfig):
    print(f"Messages: {state['messages']}")
    print(f"Plan iterations: {state.get('plan_iterations')}")
    print(f"Current plan: {state.get('current_plan')}")
```

### 3. Config 확인

```python
def my_node(state: State, config: RunnableConfig):
    conf = Configuration.from_runnable_config(config)
    print(f"Max iterations: {conf.max_plan_iterations}")
    print(f"Thread ID: {config['configurable']['thread_id']}")
```

### 4. 스트림 모드별 이벤트

```python
# "values": 전체 State (무거움)
# "updates": State 변경사항만 (가벼움)
# "messages": 메시지 청크 (실시간)

stream_mode=["messages"]  # 메시지만
stream_mode=["updates"]   # State만
stream_mode=["messages", "updates"]  # 둘 다 (권장)
```

---

## 모범 사례

### 1. 에러 처리

```python
try:
    async for event in graph.astream(...):
        yield event
except Exception as e:
    logger.exception("Graph error")
    yield {"event": "error", "data": {"message": str(e)}}
```

### 2. 로그 보안

```python
# ❌ 직접 로깅
logger.info(f"User input: {user_input}")

# ✅ sanitize 적용
safe_input = sanitize_log_input(user_input)
logger.info(f"User input: {safe_input}")
```

### 3. 타입 안정성

```python
# ❌ 타입 미지정
def process(data):
    return data["value"]

# ✅ 타입 힌트 사용
def process(data: dict[str, Any]) -> str:
    return cast(str, data.get("value", ""))
```

### 4. 제너레이터 사용

```python
# ❌ 리스트로 모두 반환 (메모리 많이 사용)
def get_all_events():
    events = []
    for event in source:
        events.append(process(event))
    return events

# ✅ 제너레이터로 하나씩 (메모리 효율적)
async def stream_events():
    async for event in source:
        yield process(event)
```

---

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [Python Async Generators](https://peps.python.org/pep-0525/)

---

## 용어 정리

| 용어            | 설명                                   |
| --------------- | -------------------------------------- |
| **SSE**         | Server-Sent Events, 서버 푸시 기술     |
| **DTO**         | Data Transfer Object, 데이터 전송 객체 |
| **State**       | LangGraph의 노드 간 공유 상태          |
| **Config**      | LangGraph의 실행 설정 (읽기 전용)      |
| **yield**       | 제너레이터에서 값을 하나씩 반환        |
| **cast**        | 타입 체커를 위한 타입 힌트             |
| **sanitize**    | 입력값을 안전하게 정제                 |
| **astream**     | LangGraph 비동기 스트리밍 실행         |
| **stream_mode** | 이벤트 타입 지정 (messages/updates)    |

---

## 요약

1. **클라이언트**는 `fetch()`로 SSE 스트림 시작
2. **FastAPI**는 `StreamingResponse`로 제너레이터 반환
3. **제너레이터**는 `yield`로 이벤트를 하나씩 전송
4. **LangGraph**는 `astream()`으로 노드 실행
5. **이벤트**는 Dict(내부용) 또는 Tuple(클라이언트용)
6. **어댑터**가 LangGraph 이벤트를 SSE로 변환
7. **클라이언트**는 실시간으로 화면에 표시

핵심은 **비동기 제너레이터를 통한 실시간 스트리밍**입니다! 🚀✨
