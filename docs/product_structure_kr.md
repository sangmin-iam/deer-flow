# DeerFlow 프로젝트 구조

## 📋 목차

- [프로젝트 개요](#프로젝트-개요)
- [전체 디렉토리 구조](#전체-디렉토리-구조)
- [핵심 모듈 설명](#핵심-모듈-설명)
- [아키텍처](#아키텍처)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [진입점 및 실행 방식](#진입점-및-실행-방식)

---

## 프로젝트 개요

**DeerFlow** (Deep Exploration and Efficient Research Flow)는 오픈소스 커뮤니티 기반의 Deep Research 프레임워크입니다. LangGraph를 기반으로 한 멀티 에이전트 시스템을 통해 웹 검색, 크롤링, Python 코드 실행 등의 도구를 활용하여 심층적인 리서치를 수행하고 종합 보고서를 생성합니다.

### 주요 특징

- 🤖 **멀티 에이전트 아키텍처**: Coordinator, Planner, Researcher, Coder, Reporter로 구성된 협업 시스템
- 🔍 **다양한 검색 엔진 지원**: Tavily, Brave Search, DuckDuckGo, Arxiv 등
- 📚 **RAG 통합**: RAGFlow, VikingDB 등 프라이빗 지식베이스 지원
- 🔗 **MCP(Model Context Protocol) 통합**: 외부 도구 및 서비스와의 seamless 통합
- 🎙️ **콘텐츠 생성**: Podcast 스크립트, PPT, TTS 기능
- 💬 **Human-in-the-loop**: 대화형 계획 수정 및 승인 기능

---

## 전체 디렉토리 구조

```
deer-flow/
├── src/                          # 백엔드 핵심 코드
│   ├── agents/                   # 에이전트 정의 및 도구 인터셉터
│   ├── config/                   # 설정 관리
│   ├── crawler/                  # 웹 크롤링 및 콘텐츠 추출
│   ├── graph/                    # LangGraph 워크플로우 정의
│   ├── llms/                     # LLM 통합 (litellm 기반)
│   ├── podcast/                  # 팟캐스트 생성 기능
│   ├── ppt/                      # PPT 생성 기능
│   ├── prompt_enhancer/          # 프롬프트 개선 기능
│   ├── prompts/                  # 각 에이전트의 프롬프트 템플릿
│   ├── prose/                    # 산문 생성 및 편집
│   ├── rag/                      # RAG 통합 (RAGFlow, VikingDB 등)
│   ├── server/                   # FastAPI 서버 및 API 엔드포인트
│   ├── tools/                    # 검색, 크롤링, Python REPL 등 도구
│   ├── utils/                    # 유틸리티 함수
│   └── workflow.py               # 워크플로우 실행 진입점
│
├── web/                          # 프론트엔드 (Next.js)
│   ├── src/                      # React 컴포넌트 및 페이지
│   ├── messages/                 # i18n 번역 파일
│   ├── public/                   # 정적 파일
│   └── docs/                     # 웹 관련 문서
│
├── docs/                         # 프로젝트 문서
│   ├── configuration_guide.md    # 설정 가이드
│   ├── FAQ.md                    # 자주 묻는 질문
│   ├── mcp_integrations.md       # MCP 통합 가이드
│   ├── API.md                    # API 문서
│   └── agent_customization_guide_ko.md  # 에이전트 커스터마이징 가이드
│
├── examples/                     # 사용 예제 및 샘플 리포트
├── tests/                        # 단위 및 통합 테스트
│   ├── unit/                     # 단위 테스트
│   └── integration/              # 통합 테스트
│
├── main.py                       # CLI 진입점
├── server.py                     # 서버 진입점
├── conf.yaml                     # LLM 및 시스템 설정
├── .env                          # 환경 변수 (API 키 등)
├── pyproject.toml                # Python 프로젝트 설정
├── langgraph.json                # LangGraph Studio 설정
├── docker-compose.yml            # Docker 구성
└── Dockerfile                    # Docker 이미지 빌드 파일
```

---

## 핵심 모듈 설명

### 1. **src/agents/** - 에이전트 정의

- `agents.py`: Coordinator, Planner, Researcher, Coder, Reporter 에이전트의 핵심 로직
- `tool_interceptor.py`: MCP 및 도구 호출 인터셉팅 및 로깅

### 2. **src/config/** - 설정 관리

- `configuration.py`: 시스템 설정 로딩 및 관리
- `loader.py`: conf.yaml 파일 파싱
- `agents.py`: 에이전트별 설정
- `tools.py`: 도구 설정
- `questions.py`: 내장 질문 목록

### 3. **src/crawler/** - 웹 크롤링

- `crawler.py`: 웹 크롤러 메인 로직
- `jina_client.py`: Jina Reader API 클라이언트
- `readability_extractor.py`: 콘텐츠 추출 (Readability 알고리즘)
- `article.py`: 기사 데이터 모델

### 4. **src/graph/** - 워크플로우 그래프

- `builder.py`: LangGraph 워크플로우 구축
- `nodes.py`: 각 에이전트 노드 정의 (1000+ 라인)
  - `coordinator_node`: 워크플로우 조율
  - `background_investigation_node`: 배경 조사
  - `planner_node`: 계획 수립
  - `researcher_node`: 웹 검색 및 정보 수집
  - `coder_node`: 코드 분석 및 실행
  - `reporter_node`: 최종 보고서 생성
  - `human_feedback_node`: 사람 피드백 처리
- `types.py`: State 정의 (워크플로우 상태)
- `checkpoint.py`: 체크포인트 저장/로드
- `utils.py`: 유틸리티 함수

### 5. **src/llms/** - LLM 통합

- `llm.py`: LiteLLM을 통한 통합 LLM 인터페이스
- `providers/`: 다양한 LLM 프로바이더 지원
  - OpenAI, Anthropic, DeepSeek, Google Gemini 등

### 6. **src/tools/** - 도구 모음

- `search.py`: 웹 검색 (Tavily, Brave, DuckDuckGo 등)
- `crawl.py`: 웹 페이지 크롤링
- `python_repl.py`: Python 코드 실행
- `retriever.py`: RAG 검색
- `tts.py`: Text-to-Speech (Volcengine)
- `tavily_search/`: Tavily 검색 커스터마이징

### 7. **src/prompts/** - 프롬프트 템플릿

각 에이전트별 프롬프트 템플릿:

- `coordinator.md`: Coordinator 시스템 프롬프트
- `planner.md`: Planner 시스템 프롬프트
- `researcher.md`: Researcher 시스템 프롬프트
- `coder.md`: Coder 시스템 프롬프트
- `reporter.md`: Reporter 시스템 프롬프트
- `planner_model.py`: 계획 데이터 모델 (Pydantic)

다국어 지원:

- `*_ko.md`: 한국어 프롬프트
- `*_zh_CN.md`: 중국어 프롬프트

### 8. **src/server/** - API 서버

- `app.py`: FastAPI 애플리케이션 정의
- `chat_request.py`: 채팅 API 엔드포인트
- `config_request.py`: 설정 API
- `mcp_request.py`: MCP 관련 API
- `rag_request.py`: RAG 관련 API
- `mcp_utils.py`: MCP 유틸리티

### 9. **src/rag/** - RAG 통합

- `builder.py`: RAG 시스템 빌더
- `retriever.py`: 통합 리트리버
- `ragflow.py`: RAGFlow 통합
- `vikingdb_knowledge_base.py`: VikingDB 통합
- `milvus.py`: Milvus 벡터 DB 통합
- `dify.py`: Dify 플랫폼 통합
- `moi.py`: MOI 통합

### 10. **src/podcast/** - 팟캐스트 생성

- `graph/`: 팟캐스트 생성 워크플로우
- `types.py`: 팟캐스트 데이터 모델

### 11. **src/ppt/** - PPT 생성

- `graph/`: PPT 생성 워크플로우 (Marp 기반)

### 12. **src/prompt_enhancer/** - 프롬프트 개선

- `graph/`: 프롬프트 개선 워크플로우

### 13. **src/prose/** - 산문 생성

- `graph/`: 산문 생성 및 편집 워크플로우

### 14. **web/** - 프론트엔드

Next.js 기반 웹 인터페이스:

- React 컴포넌트
- Notion 스타일 블록 에디터 (tiptap 기반)
- 다국어 지원 (i18n)
- 실시간 스트리밍 UI
- 사고 과정 블록 표시

---

## 아키텍처

### 멀티 에이전트 워크플로우

DeerFlow는 LangGraph 기반의 상태 머신 아키텍처를 사용합니다:

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Coordinator     │  ← 진입점, 워크플로우 조율
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  Background      │  ← 선택적 배경 조사
│  Investigator    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│    Planner       │  ← 연구 계획 수립
└──────┬───────────┘      │
       │                  │ (Human Feedback)
       ▼                  ▼
┌──────────────────┐  ┌────────────────┐
│  Research Team   │  │ Human Feedback │
└──────┬───────────┘  └────────────────┘
       │
       ├─ Researcher  ← 웹 검색, 정보 수집
       │
       └─ Coder       ← 코드 분석, Python 실행
       │
       ▼
┌──────────────────┐
│    Reporter      │  ← 최종 보고서 생성
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│      END         │
└──────────────────┘
```

### 주요 에이전트 역할

1. **Coordinator**:

   - 사용자 입력 분석
   - 워크플로우 시작 결정
   - Clarification 기능 (불명확한 질문 명확화)

2. **Background Investigator**:

   - 계획 수립 전 배경 조사 수행
   - 검색을 통한 컨텍스트 수집

3. **Planner**:

   - 연구 계획(Research Plan) 생성
   - 단계별 작업(Step) 정의
   - 계획 반복 및 개선

4. **Research Team**:

   - **Researcher**: 웹 검색, 크롤링, MCP 도구 활용
   - **Coder**: 데이터 분석, Python 코드 실행

5. **Reporter**:
   - 수집된 정보를 종합
   - 구조화된 보고서 생성
   - 이미지 및 참고자료 포함

### 상태(State) 관리

워크플로우는 `State` 객체를 통해 상태를 공유합니다:

```python
State = {
    "messages": List[Message],           # 대화 히스토리
    "research_topic": str,               # 연구 주제
    "current_plan": ResearchPlan,        # 현재 계획
    "iteration": int,                    # 반복 횟수
    "context": dict,                     # 수집된 컨텍스트
    "final_report": str,                 # 최종 보고서
    "auto_accepted_plan": bool,          # 자동 승인 여부
    "enable_clarification": bool,        # 명확화 활성화 여부
    # ... 기타 상태 필드
}
```

---

## 주요 기능

### 1. 검색 및 정보 수집

- **다중 검색 엔진**: Tavily, Brave Search, DuckDuckGo, Arxiv
- **웹 크롤링**: Jina Reader API 또는 Readability 알고리즘
- **RAG 통합**: 프라이빗 문서 검색

### 2. MCP(Model Context Protocol) 통합

- 외부 도구 및 서비스 연동
- GitHub Trending, 지식 그래프 등
- 설정 파일 기반 동적 로딩

### 3. Human-in-the-loop

- **계획 검토**: 계획 생성 후 사용자 승인/수정
- **Clarification**: 불명확한 질문에 대한 대화형 명확화
- **Report Editing**: Notion 스타일 블록 편집

### 4. 콘텐츠 생성

- **Podcast**: AI 기반 스크립트 생성 및 TTS
- **PPT**: Marp 기반 프레젠테이션 생성
- **Report**: Markdown 형식의 구조화된 보고서

### 5. 체크포인트 및 재생

- **PostgreSQL/MongoDB**: 워크플로우 상태 저장
- **대화 재생**: 이전 대화 재개
- **스트리밍 이벤트 저장**: 대화 재생 기능

### 6. 다국어 지원

- 한국어(ko), 중국어(zh), 영어(en)
- 프롬프트 및 UI 번역

---

## 기술 스택

### 백엔드

- **언어**: Python 3.12+
- **프레임워크**:
  - LangGraph: 멀티 에이전트 워크플로우
  - LangChain: LLM 통합 및 도구 체인
  - FastAPI: REST API 서버
  - Uvicorn: ASGI 서버
- **LLM 통합**: LiteLLM (OpenAI, Anthropic, DeepSeek, Gemini 등)
- **데이터베이스**:
  - PostgreSQL: 체크포인트 저장
  - MongoDB: 체크포인트 저장
  - Milvus: 벡터 검색
- **검색**: Tavily, Brave, DuckDuckGo, Arxiv
- **크롤링**: Jina Reader, Readability
- **TTS**: Volcengine Text-to-Speech

### 프론트엔드

- **프레임워크**: Next.js 22+
- **UI 라이브러리**: React, TailwindCSS
- **에디터**: Tiptap (Notion-like WYSIWYG)
- **상태 관리**: React Hooks
- **i18n**: next-intl

### DevOps

- **컨테이너**: Docker, Docker Compose
- **패키지 관리**:
  - Python: uv, pip
  - Node.js: pnpm
- **테스트**: pytest, jest
- **린팅**: ruff (Python), ESLint (TypeScript)

---

## 진입점 및 실행 방식

### 1. CLI 모드 (main.py)

콘솔 기반 대화형 인터페이스:

```bash
# 직접 질문 입력
uv run main.py "What is quantum computing?"

# 대화형 모드
uv run main.py --interactive

# 디버그 모드
uv run main.py --debug "Research topic"

# 옵션 설정
uv run main.py --max_plan_iterations 3 --max_step_num 5 "topic"
```

### 2. 서버 모드 (server.py)

FastAPI 기반 REST API:

```bash
# 서버 시작
uv run server.py --host 0.0.0.0 --port 8000

# 디버그 모드
uv run server.py --log-level debug --reload
```

주요 API 엔드포인트:

- `POST /api/chat`: 채팅 스트리밍
- `POST /api/tts`: Text-to-Speech
- `GET /api/config`: 설정 조회
- `POST /api/mcp/servers`: MCP 서버 관리
- `POST /api/rag`: RAG 검색

### 3. 웹 UI 모드

Next.js 프론트엔드와 함께 실행:

```bash
# 전체 스택 실행 (백엔드 + 프론트엔드)
./bootstrap.sh -d  # macOS/Linux
bootstrap.bat -d   # Windows

# 또는 Docker Compose
docker compose up
```

웹 UI 기능:

- 실시간 스트리밍 응답
- 사고 과정(Thought Block) 표시
- Notion 스타일 보고서 편집
- 대화 히스토리 관리
- 다국어 UI

### 4. LangGraph Studio (디버깅)

워크플로우 시각화 및 디버깅:

```bash
# Mac
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.12 langgraph dev --allow-blocking

# Windows/Linux
pip install -e .
pip install -U "langgraph-cli[inmem]"
langgraph dev
```

Studio 기능:

- 워크플로우 그래프 시각화
- 실시간 실행 추적
- 각 노드의 입출력 검사
- Human feedback 제공

---

## 설정 파일

### conf.yaml

LLM 및 에이전트 설정:

```yaml
llm:
  temperature: 0.7
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4
    # ...

agents:
  coordinator:
    enabled: true
    llm: openai/gpt-4
  planner:
    enabled: true
    llm: openai/gpt-4
  # ...
```

### .env

환경 변수 및 API 키:

```bash
# 검색 엔진
SEARCH_API=tavily
TAVILY_API_KEY=xxx
BRAVE_SEARCH_API_KEY=xxx

# LLM
OPENAI_API_KEY=xxx
ANTHROPIC_API_KEY=xxx

# 체크포인트
LANGGRAPH_CHECKPOINT_SAVER=true
LANGGRAPH_CHECKPOINT_DB_URL=mongodb://localhost:27017/

# LangSmith (선택)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=xxx
```

---

## 개발 워크플로우

### 테스트

```bash
# 전체 테스트
make test

# 특정 테스트
pytest tests/integration/test_workflow.py

# 커버리지
make coverage
```

### 코드 품질

```bash
# 린팅
make lint

# 포맷팅
make format
```

### 디버깅

- LangGraph Studio 사용
- LangSmith 트레이싱 활성화
- `--debug` 플래그로 상세 로그 확인

---

## 확장 및 커스터마이징

### 새 에이전트 추가

1. `src/agents/agents.py`에 에이전트 함수 정의
2. `src/prompts/`에 프롬프트 추가
3. `src/graph/nodes.py`에 노드 함수 추가
4. `src/graph/builder.py`에서 그래프에 연결

### 새 도구 추가

1. `src/tools/`에 도구 모듈 생성
2. `@tool` 데코레이터로 함수 정의
3. 에이전트에 도구 바인딩

### MCP 서버 통합

1. `conf.yaml` 또는 `workflow.py`의 `mcp_settings`에 설정 추가
2. 활성화할 도구 및 에이전트 지정

---

## 참고 문서

- [Configuration Guide](./configuration_guide.md): 상세 설정 가이드
- [Agent Customization Guide](./agent_customization_guide_ko.md): 에이전트 커스터마이징
- [MCP Integrations](./mcp_integrations.md): MCP 통합 가이드
- [FAQ](./FAQ.md): 자주 묻는 질문
- [API Documentation](./API.md): API 레퍼런스

---

## 라이선스

MIT License

## 기여

커뮤니티 기여를 환영합니다! `CONTRIBUTING` 파일을 참조하세요.

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-11-04
