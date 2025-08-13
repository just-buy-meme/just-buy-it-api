<div align="center">
  <img src="https://github.com/user-attachments/assets/b4a6de8b-136b-44f9-b65d-546d58c854a3" alt="한국투자증권 로고" width="150"/>
  <h1>한국투자증권 x 가짜연구소</h1>
  <h2>미국 밈주식(Meme Stock) 중심 주식 정보 검색 및 자동매매를 위한 LLM 기반 AI Agent</h2>
</div>

> 본 프로젝트는 **한국투자증권**과 AI 개발자 커뮤니티 **가짜연구소**의 협력을 통해 진행되는 '미국 밈주식(Meme Stock) 중심 주식 정보 검색 및 자동매매를 위한 LLM 기반 AI Agent 챗봇' 프로젝트입니다.

---

## 1. 프로젝트 개요 (Project Overview)

본 프로젝트는 소셜 미디어와 온라인 커뮤니티에서 발생하는 집단적 투자 심리로 급격한 가격 변동을 보이는 **'밈주식'**에 주목합니다. LLM 기반의 AI Agent가 웹의 방대한 자료를 실시간으로 수집하고, 과거 거래 패턴을 분석하여 잠재적 밈주식을 탐지하고 매수 시그널을 제안합니다.

이를 통해, 아직 해외주식 경험이 없는 고객들에게 **'적은 금액으로 재미있게 시작하는 유쾌한 첫 거래 경험'**을 제공하는 것을 목표로 합니다.

---

## 2. 주요 목표 및 기대효과 (Objectives & Expected Outcomes)

본 AI Agent 개발을 통해 다음과 같은 비즈니스 및 브랜딩 효과를 기대합니다.

* **신규 고객 확보 및 수익 증대**
    * 차별화된 밈주식 콘텐츠로 신규 해외주식 거래 고객을 유치하고 약정 금액을 증대시킵니다.
    * 과도한 수수료 경쟁에서 벗어나, 독자적인 콘텐츠로 새로운 수익을 창출하는 선순환 구조를 수립합니다.
* **긍정적 바이럴 및 커뮤니티 형성**
    * 최신 AI Agent 기술과 '밈주식'이라는 흥미로운 소재의 결합으로 투자 커뮤니티로부터 긍정적인 바이럴 효과를 창출합니다.
* **AI 기술 선도 이미지 구축**
    * 최신 AI 기술을 금융 서비스에 적극적으로 활용함으로써, 자본 시장의 'AI 기술 선도자'로서 한국투자증권의 브랜드 이미지를 제고하고 시장 지위를 공고히 합니다.

---

## 3. 핵심 기능 (Core Features)

본 챗봇은 다음과 같은 전문 에이전트들의 유기적인 협력을 통해 동작하며, 사용자의 요청을 단계적으로 처리합니다.

* **🤖 슈퍼바이저 에이전트 (Supervisor Agent)**
    * **역할:** 사용자의 요청을 가장 먼저 받아 분석하고, 어떤 에이전트에게 작업을 전달할지 결정하는 등 전체 워크플로우를 총괄 지휘합니다.

* **🗓️ 플래너 에이전트 (Planner Agent)**
    * **역할:** 사용자의 복잡한 질문을 해결하기 위한 최적의 실행 계획(Step-by-step)을 수립합니다.

* **📈 밈주식 탐지 에이전트 (Meme Stock Detection Agent)**
    * **역할:** 소셜 데이터를 실시간으로 크롤링하고 분석하여 잠재적 밈주식을 추천합니다.

* **📊 주식 정보 에이전트 (Stock Info Agent)**
    * **역할:** 한국투자증권 API를 활용해 특정 종목의 시세, 차트 등 상세 정보를 조회합니다.

* **💼 계좌 정보 에이전트 (Account Info Agent)**
    * **역할:** 계좌 잔고, 보유 종목, 기간별 손익, 일별 체결 내역 등 자산 정보를 조회합니다.

* **⚙️ 매매 에이전트 (Trading Agent)**
    * **역할:** 플래너가 수립한 계획에 따라, 사용자의 최종 승인을 거쳐 매수/매도 주문을 실행합니다.

---

## 4. 시스템 아키텍처 (System Architecture)

본 프로젝트는 아래와 같이 여러 전문 에이전트가 협력하는 멀티 에이전트(Multi-Agent) 시스템으로 구성됩니다.

<div align="center">
  <img src="https://github.com/user-attachments/assets/0db7a307-95aa-4ba0-82eb-9b4a78c6d7d4" alt="시스템 아키텍처 다이어그램" width="720" />
</div>

| 구분 | 주요 역할 | 기술 스택 |
| :--- | :--- | :--- |
| **데이터 수집/처리** | 밈주식 추천 소스 데이터 크롤링 및 DB 저장 | `Airflow`, `BeautifulSoup`, `Pandas`, `PostgreSQL` |
| **AI 에이전트** | 정보 탐색, 자동 매매 등 핵심 기능 수행 | `LangGraph`, `LLM (GPT-4o)`, `FastAPI` |
| **인터페이스/배포** | 사용자 챗봇 UI 및 서비스 배포 | `Streamlit`, `Docker`, `AWS EC2` |
| **핵심 API** | 주식 데이터 및 거래 실행 | **한국투자증권 API** |

---

## 5. 개발 환경 (Development)

### Docker compose for development
```bash
docker compose watch

## Development

### Docker compose for development
```bash
docker compose watch
```
Automatic interactive documentation with Swagger UI (from the OpenAPI backend):
-  http://localhost:8888/docs

for details see [backend/README.md](backend/README.md)


### Pre-commits and code linting
```bash
uv run pre-commit install
```

### Package install
```bash
uv add $PACKAGE
```

### Testing
```bash
docker compose build
docker compose up -d
docker compose exec -T backend bash scripts/tests-start.sh
```
