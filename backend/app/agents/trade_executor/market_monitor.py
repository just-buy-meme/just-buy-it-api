import sys
import os
import requests  # ✅ FastAPI 서버 호출 추가
import asyncio
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.core.deps import llm, thinking_llm, embeddings, kis

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
sys.path.insert(0, backend_dir)

from app.agents.module.module import TickerResolver

# FastAPI 서버 주소
FASTAPI_SERVER_URL = "http://localhost:8888/api/v1"  # 너의 서버 주소에 맞게 수정
# LLM 세팅

# ✅ FastAPI 서버로 모니터링 요청 보내기
def send_monitoring_request(tickers, budget):
    try:
        response = requests.post(
            f"{FASTAPI_SERVER_URL}/start_monitoring",
            json={"tickers": tickers, "budget": budget}
        )
        if response.status_code == 200:
            print(f"✅ FastAPI 서버에 모니터링 요청 성공! (Tickers: {tickers}, Budget: {budget})")
        else:
            print(f"❌ FastAPI 서버 오류: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ FastAPI 서버 요청 실패: {str(e)}")

class MonitoringStock(BaseModel):
    tickers : list = Field(description = "streamlit에서 전달된 종목 리스트")
    budget : int = Field(description = "사용자가 모니터링에 사용하기 원하는 예산")

@tool(args_schema = MonitoringStock)
def get_monitoring_stock(tickers : list[str], budget : int) -> dict:
    """
    시장 자동 모니터링을 시작합니다.
    동시에 FastAPI 서버로 비동기 모니터링 요청을 전송합니다.
    """
    usd_depo = float(kis.account().balance().deposits['USD'].amount)
    usd_depo = 10000
    if budget > usd_depo * 0.8:
        raise ValueError(f"입력한 예산 ${budget}은 현재 USD 잔고의 80%를 초과했습니다.")

    per_stock = budget // len(tickers)
    valid_tickers = []

    for ticker in tickers:
        stock_cp = float(kis.stock(ticker).quote().price)
        if stock_cp <= per_stock:
            valid_tickers.append(ticker)

    send_monitoring_request(valid_tickers, budget)

    return {
        "accepted_tickers": valid_tickers,
        "budget_used": budget
    }


def create_market_monitor_agent():
    return create_react_agent(
        llm,
        tools=[get_monitoring_stock],
        name="market_monitoring_agent",
        prompt=(
            "당신은 사용자가 원하는 종목에 대해 틱 단위의 실시간 거래상황을 모니터링하고 필요시 자동매매까지 할 수 있도록 fastapi 백엔드에 시그널을 전달하는 에이전트입니다. "
            "또한 사용자가 자동매매에 사용할 예산이 실제 잔고보다 적은지 판단하고 매매 가능한 종목 리스트만을 남겨줍니다. "
            "일단 tool을 실행하면 곧바로 해당 예산 정보와 종목 리스트를 fastapi 백엔드에 넘겨줍니다. **절대로 무한루프는 없습니다**"
            "이후 슈퍼바이저에게 사용자가 입력한 종목 중 어떤 종목이 자동매매 가능한지, 그리고 사용자가 사용할 예산은 몇달러인지 결과를 리턴합니다.."
        )
    )