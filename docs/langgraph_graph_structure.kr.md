# LangGraph 그래프 구조 가이드

이 문서는 Deer Flow 프로젝트의 LangGraph 그래프 구조와 노드 연결 방식을 설명합니다.

## 목차

1. [그래프 구조 개요](#그래프-구조-개요)
2. [노드 설명](#노드-설명)
3. [라우팅 방식](#라우팅-방식)
4. [실제 흐름 예시](#실제-흐름-예시)
5. [코드 위치](#코드-위치)

---

## 그래프 구조 개요

### 전체 구조 다이어그램

```
START
  ↓
┌─────────────┐
│ coordinator │ ←──────────────────┐
└─────────────┘                    │
  ↓ (동적 라우팅)                  │ (명확화 루프)
  ├→ background_investigator       │
  │    ↓ (고정 엣지)                │
  │  ┌─────────┐                   │
  │  │ planner │ ←─────────────────┤
  │  └─────────┘                   │
  │    ↓ (동적 라우팅)             │
  │    ├→ human_feedback           │
  │    │    ↓ (동적 라우팅)        │
  │    │    ├→ research_team ──┐   │
  │    │    │    ↓ (조건부)    │   │
  │    │    │    ├→ researcher │   │
  │    │    │    │  (서브그래프)│   │
  │    │    │    │              │   │
  │    │    │    ├→ coder      │   │
  │    │    │    │  (서브그래프)│   │
  │    │    │    │              │   │
  │    │    │    └→ planner ←──┘   │
  │    │    │                       │
  │    │    ├→ planner (재계획) ───┘
  │    │    ├→ reporter
  │    │    └→ END
  │    │
  │    └→ reporter
  │         ↓ (고정 엣지)
  │       END
  │
  ├→ planner (background 스킵)
  ├→ coordinator (자기 자신, 명확화)
  └→ END (종료)
```

### 구조 범례

| 기호            | 의미                           |
| --------------- | ------------------------------ |
| `→`             | 엣지 (연결)                    |
| `├→`            | 분기                           |
| `↓`             | 순차 진행                      |
| `←`             | 루프백                         |
| `(고정 엣지)`   | builder.py에서 정의            |
| `(동적 라우팅)` | 노드의 Command 반환값으로 결정 |
| `(조건부)`      | 조건 함수로 결정               |
| `(서브그래프)`  | 내부에 agent 구조 있음         |

---

## 노드 설명

### 1. Coordinator (코디네이터)

**역할:** 워크플로우 시작점, 사용자와 대화, 질문 명확화

**파일:** `src/graph/nodes.py` - `coordinator_node()`

**반환 타입:**

```python
Command[Literal[
    "planner",                  # 직접 플래너로
    "background_investigator",  # 배경 조사로 (일반적)
    "coordinator",              # 자기 자신 (명확화 루프)
    "__end__"                   # 종료
]]
```

**가능한 경로:**

- ✅ coordinator → background_investigator (일반적, `enable_background_investigation=True`)
- ✅ coordinator → planner (background 스킵)
- ✅ coordinator → coordinator (명확화 모드, 질문-답변 반복)
- ✅ coordinator → END (종료)

**결정 로직:**

```python
# 1. Tool call 확인
if tool_name in ["handoff_to_planner", "handoff_after_clarification"]:
    goto = "planner"

# 2. 배경 조사 활성화 여부
if goto == "planner" and state.get("enable_background_investigation"):
    goto = "background_investigator"

# 3. 명확화 모드
if not tool_calls and enable_clarification:
    goto = "coordinator"  # 자기 자신으로 루프
```

---

### 2. Background Investigator (배경 조사)

**역할:** 연구 주제의 배경 정보 수집

**파일:** `src/graph/nodes.py` - `background_investigation_node()`

**반환 타입:** 없음 (고정 엣지)

**가능한 경로:**

- ✅ background_investigator → planner (고정, `builder.add_edge()`)

**결정 로직:**

- builder.py에서 고정 엣지로 정의됨

---

### 3. Planner (계획 수립)

**역할:** 연구 계획 생성, 스텝 정의

**파일:** `src/graph/nodes.py` - `planner_node()`

**반환 타입:**

```python
Command[Literal[
    "human_feedback",  # 사용자 승인 요청 (일반적)
    "reporter"         # 바로 보고서 작성 (플랜 없음)
]]
```

**가능한 경로:**

- ✅ planner → human_feedback (일반적, `auto_accepted_plan=False`)
- ✅ planner → reporter (플랜 생성 실패, 바로 종료)

**결정 로직:**

```python
if not current_plan or not current_plan.steps:
    # 플랜 생성 실패
    goto = "reporter"
else:
    # 정상 플랜 생성
    goto = "human_feedback"
```

---

### 4. Human Feedback (사용자 피드백)

**역할:** 플랜 검토 및 사용자 승인 처리

**파일:** `src/graph/nodes.py` - `human_feedback_node()`

**반환 타입:**

```python
Command[Literal[
    "planner",        # 플랜 수정 요청
    "research_team",  # 승인, 연구 시작
    "reporter",       # 바로 보고서
    "__end__"         # 종료
]]
```

**가능한 경로:**

- ✅ human_feedback → research_team (승인, `feedback="accepted"`)
- ✅ human_feedback → planner (거부, `feedback="edit_plan"`)
- ✅ human_feedback → reporter (중단 후 바로 종료)
- ✅ human_feedback → END (작업 취소)

**결정 로직:**

```python
# Auto accept 체크
if auto_accepted_plan:
    goto = "research_team"
else:
    # Interrupt로 사용자 대기
    feedback = interrupt("Please Review the Plan.")

    if feedback == "accepted":
        goto = "research_team"
    elif feedback == "edit_plan":
        goto = "planner"
    else:
        goto = "reporter"
```

---

### 5. Research Team (연구팀 조정)

**역할:** 연구 작업 조정, researcher/coder로 분배

**파일:** `src/graph/nodes.py` - `research_team_node()`

**반환 타입:** 없음 (조건부 엣지)

**가능한 경로:**

- ✅ research_team → researcher (RESEARCH 타입 스텝)
- ✅ research_team → coder (PROCESSING 타입 스텝)
- ✅ research_team → planner (모든 스텝 완료)

**결정 로직:** (builder.py의 `continue_to_running_research_team`)

```python
def continue_to_running_research_team(state: State):
    current_plan = state.get("current_plan")

    # 플랜 없음 → planner로
    if not current_plan or not current_plan.steps:
        return "planner"

    # 모든 스텝 완료 → planner로
    if all(step.execution_res for step in current_plan.steps):
        return "planner"

    # 미완료 스텝 찾기
    for step in current_plan.steps:
        if not step.execution_res:
            if step.step_type == StepType.RESEARCH:
                return "researcher"
            if step.step_type == StepType.PROCESSING:
                return "coder"

    return "planner"
```

---

### 6. Researcher (연구원) - 서브그래프

**역할:** 검색, 정보 수집

**파일:** `src/graph/nodes.py` - `researcher_node()`

**반환 타입:**

```python
Command[Literal["research_team"]]  # 항상 research_team으로 복귀
```

**내부 구조 (서브그래프):**

```
__start__
    ↓
  agent
    ↓ (도구 호출)
  tools (search, crawl, etc.)
    ↓
  agent (결과 처리)
    ↓
  __end__
```

**가능한 경로:**

- ✅ researcher → research_team (항상)

---

### 7. Coder (코더) - 서브그래프

**역할:** 데이터 처리, 코드 실행, 분석

**파일:** `src/graph/nodes.py` - `coder_node()`

**반환 타입:**

```python
Command[Literal["research_team"]]  # 항상 research_team으로 복귀
```

**내부 구조 (서브그래프):**

```
__start__
    ↓
  agent
    ↓ (도구 호출)
  tools (python_repl, etc.)
    ↓
  agent (결과 처리)
    ↓
  __end__
```

**가능한 경로:**

- ✅ coder → research_team (항상)

---

### 8. Reporter (보고서 작성)

**역할:** 최종 보고서 생성

**파일:** `src/graph/nodes.py` - `reporter_node()`

**반환 타입:** 없음 (고정 엣지)

**가능한 경로:**

- ✅ reporter → END (고정, `builder.add_edge()`)

---

## 라우팅 방식

### 1. 고정 엣지 (Static Edges)

**정의 위치:** `src/graph/builder.py`

**코드:**

```python
def _build_base_graph():
    builder = StateGraph(State)

    # 고정 엣지 정의
    builder.add_edge(START, "coordinator")                  # ✅
    builder.add_edge("background_investigator", "planner")  # ✅
    builder.add_edge("reporter", END)                       # ✅

    return builder
```

**특징:**

- 항상 같은 경로
- 조건 없이 다음 노드로 진행
- builder.py에서 명시적으로 정의

---

### 2. 동적 라우팅 (Dynamic Routing)

**정의 위치:** 각 노드의 `Command` 반환값

**코드 예시:**

```python
def coordinator_node(state, config) -> Command[Literal["planner", "background_investigator", ...]]:
    # 로직 수행
    # ...

    # 다음 노드 결정
    if some_condition:
        goto = "background_investigator"
    else:
        goto = "planner"

    return Command(
        update={...},
        goto=goto  # ← 여기서 다음 노드 동적 결정
    )
```

**특징:**

- 런타임에 조건에 따라 결정
- State나 Config 값에 기반
- 노드마다 다른 분기 로직

**확인 방법:**

```python
# nodes.py에서 함수 시그니처 확인
def my_node(...) -> Command[Literal["node1", "node2", "node3"]]:
    #                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                          가능한 다음 노드들
```

---

### 3. 조건부 엣지 (Conditional Edges)

**정의 위치:** `src/graph/builder.py`

**코드:**

```python
def _build_base_graph():
    builder = StateGraph(State)

    # 조건부 엣지 정의
    builder.add_conditional_edges(
        "research_team",                    # 출발 노드
        continue_to_running_research_team,  # 조건 함수
        ["planner", "researcher", "coder"]  # 가능한 목적지 노드들
    )

    return builder

# 조건 함수
def continue_to_running_research_team(state: State):
    # State를 보고 다음 노드 결정
    current_plan = state.get("current_plan")

    # ... 로직 ...

    return "researcher"  # 또는 "coder", "planner"
```

**특징:**

- 별도의 조건 함수로 분리
- State만 받아서 판단 (Config 접근 불가)
- 여러 노드가 같은 조건 함수 사용 가능

---

### 라우팅 방식 비교

| 방식            | 정의 위치          | 결정 시점 | 유연성 | 예시                 |
| --------------- | ------------------ | --------- | ------ | -------------------- |
| **고정 엣지**   | builder.py         | 컴파일 시 | 낮음   | background → planner |
| **동적 라우팅** | nodes.py (Command) | 런타임    | 높음   | coordinator → ?      |
| **조건부 엣지** | builder.py (함수)  | 런타임    | 중간   | research_team → ?    |

---

## 실제 흐름 예시

### 예시 1: 일반적인 연구 흐름

```
사용자: "파이썬이 뭐야?"

START
  ↓
coordinator
  ↓ (enable_background_investigation=True)
background_investigator
  ↓ (고정 엣지)
planner (플랜 생성)
  ↓ (current_plan 있음)
human_feedback
  ↓ (interrupt, 사용자 승인 대기)
[사용자: "accepted"]
  ↓
research_team
  ↓ (step_type=RESEARCH, 미완료)
researcher (검색 실행)
  ↓ (완료)
research_team
  ↓ (step_type=PROCESSING, 미완료)
coder (데이터 처리)
  ↓ (완료)
research_team
  ↓ (모든 스텝 완료)
planner (재평가)
  ↓ (작업 완료)
reporter (보고서 작성)
  ↓ (고정 엣지)
END
```

---

### 예시 2: 명확화 흐름

```
사용자: "그거"

START
  ↓
coordinator
  ↓ (enable_clarification=True)
coordinator (AI: "무엇에 대해 알고 싶으신가요?")
  ↓
[사용자: "파이썬"]
  ↓
coordinator (AI: "파이썬의 어떤 측면을 알고 싶으신가요?")
  ↓
[사용자: "기본 문법"]
  ↓
coordinator (LLM이 handoff_to_planner 호출)
  ↓ (enable_background_investigation=True)
background_investigator
  ↓
planner
  ... (이하 동일)
```

---

### 예시 3: 플랜 수정 흐름

```
START → coordinator → background_investigator → planner
  ↓
human_feedback (플랜 제시)
  ↓
[사용자: "edit_plan" - 스텝 2를 수정해주세요]
  ↓
planner (플랜 재생성)
  ↓
human_feedback (수정된 플랜 제시)
  ↓
[사용자: "accepted"]
  ↓
research_team → researcher/coder → ...
```

---

### 예시 4: Auto Accept 흐름

```
START
  ↓
coordinator (auto_accepted_plan=True)
  ↓
background_investigator
  ↓
planner
  ↓
human_feedback
  ↓ (auto_accepted_plan=True, interrupt 스킵)
research_team
  ... (바로 연구 시작, 사용자 대기 없음)
```

---

## 코드 위치

### 1. 그래프 구조 정의

**파일:** `src/graph/builder.py`

```python
# 노드 추가
builder.add_node("coordinator", coordinator_node)
builder.add_node("planner", planner_node)
# ...

# 고정 엣지
builder.add_edge(START, "coordinator")
builder.add_edge("background_investigator", "planner")
builder.add_edge("reporter", END)

# 조건부 엣지
builder.add_conditional_edges(
    "research_team",
    continue_to_running_research_team,
    ["planner", "researcher", "coder"]
)
```

---

### 2. 노드 구현

**파일:** `src/graph/nodes.py`

각 노드 함수 위치:

- `coordinator_node()` - 433줄
- `planner_node()` - 241줄
- `human_feedback_node()` - 350줄
- `research_team_node()` - 751줄
- `researcher_node()` - 1005줄
- `coder_node()` - 1032줄
- `reporter_node()` - 703줄
- `background_investigation_node()` - 196줄

**반환 타입 확인:**

```python
# 함수 시그니처에서 가능한 경로 확인
def coordinator_node(...) -> Command[Literal["planner", "background_investigator", ...]]:
    #                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                                   이 노드에서 갈 수 있는 모든 경로
```

**goto 결정 로직:**

```python
# 함수 내부에서 return Command(...) 찾기
return Command(
    update={...},
    goto=goto  # ← 실제 다음 노드
)
```

---

### 3. State 타입

**파일:** `src/graph/types.py`

```python
class State(MessagesState):
    messages: list
    plan_iterations: int
    current_plan: Plan | str
    observations: list[str]
    auto_accepted_plan: bool
    enable_background_investigation: bool
    enable_clarification: bool
    # ...
```

---

### 4. 서브그래프 (Agent)

**파일:** `src/agents/agents.py`

```python
def create_agent(
    agent_name: str,
    agent_type: str,
    tools: list,
    prompt_template: str,
    # ...
):
    """에이전트 생성 (researcher, coder 내부 구조)"""
```

---

## 확인 방법

### 1. 특정 노드의 가능한 경로 확인

```bash
# nodes.py에서 함수 시그니처 검색
grep "def coordinator_node" src/graph/nodes.py -A 2
```

결과:

```python
def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "coordinator", "__end__"]]:
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                       가능한 다음 노드들
```

---

### 2. 실제 goto 로직 확인

```python
# nodes.py 파일 내에서 "return Command" 검색
# coordinator_node 내부에서:

if goto == "planner" and state.get("enable_background_investigation"):
    goto = "background_investigator"

return Command(
    update={...},
    goto=goto  # ← 여기서 실제 결정
)
```

---

### 3. 조건부 분기 함수 확인

```bash
# builder.py에서 조건 함수 검색
grep "add_conditional_edges" src/graph/builder.py -A 5
```

결과:

```python
builder.add_conditional_edges(
    "research_team",
    continue_to_running_research_team,  # ← 이 함수 확인
    ["planner", "researcher", "coder"]
)
```

---

### 4. 고정 엣지 확인

```bash
# builder.py에서 고정 엣지 검색
grep "add_edge" src/graph/builder.py
```

결과:

```python
builder.add_edge(START, "coordinator")
builder.add_edge("background_investigator", "planner")
builder.add_edge("reporter", END)
```

---

## 디버깅 팁

### 1. 실행 경로 추적

로그 활성화:

```python
logger.debug(f"Current node: {node_name}")
logger.debug(f"Next goto: {goto}")
logger.debug(f"State: {state}")
```

---

### 2. State 확인

```python
def my_node(state: State, config: RunnableConfig):
    print(f"Current plan: {state.get('current_plan')}")
    print(f"Plan iterations: {state.get('plan_iterations')}")
    print(f"Auto accepted: {state.get('auto_accepted_plan')}")
```

---

### 3. 분기 조건 확인

```python
# research_team 분기 디버깅
def continue_to_running_research_team(state: State):
    plan = state.get("current_plan")
    print(f"Plan: {plan}")
    print(f"Steps: {plan.steps if plan else 'None'}")

    for step in plan.steps:
        print(f"Step: {step.title}, Type: {step.step_type}, Done: {step.execution_res}")
```

---

## 노드 추가 가이드

새로운 노드를 추가하려면:

### 1. nodes.py에 노드 함수 작성

```python
def my_new_node(
    state: State, config: RunnableConfig
) -> Command[Literal["next_node1", "next_node2"]]:
    """새 노드 설명"""

    # 로직 수행
    # ...

    # 다음 노드 결정
    goto = "next_node1"

    return Command(
        update={"some_field": "value"},
        goto=goto
    )
```

---

### 2. builder.py에 노드 등록

```python
from .nodes import my_new_node

def _build_base_graph():
    builder = StateGraph(State)

    # 노드 추가
    builder.add_node("my_new_node", my_new_node)

    # 엣지 연결
    builder.add_edge("some_node", "my_new_node")  # 고정 엣지
    # 또는
    # 기존 노드의 Command 반환 타입에 "my_new_node" 추가
```

---

### 3. State 타입 업데이트 (필요시)

```python
# types.py
class State(MessagesState):
    # ... 기존 필드
    my_new_field: str = ""  # 새 필드 추가
```

---

## 요약

### 핵심 포인트

1. **정적 구조**는 `builder.py`에서 정의
2. **동적 라우팅**은 각 노드의 `Command(goto=...)` 반환값
3. **조건부 분기**는 별도 함수로 분리 (builder.py)
4. **서브그래프**는 researcher/coder 내부의 agent 구조
5. **가능한 경로**는 `Command[Literal[...]]` 타입 힌트에서 확인

### 확인 체크리스트

- [ ] 노드 함수의 `Command[Literal[...]]` 타입 확인
- [ ] 노드 내부의 `return Command(goto=...)` 로직 확인
- [ ] builder.py의 `add_edge()` 확인 (고정 엣지)
- [ ] builder.py의 `add_conditional_edges()` 확인
- [ ] 조건 함수의 분기 로직 확인

---

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangGraph Command API](https://langchain-ai.github.io/langgraph/reference/graphs/#command)
- [Conditional Edges](https://langchain-ai.github.io/langgraph/how-tos/branching/)

---

## 관련 문서

- [LangGraph 스트리밍 아키텍처](./langgraph_streaming_architecture.md)
- [프로젝트 구조](./product_structure.md)
