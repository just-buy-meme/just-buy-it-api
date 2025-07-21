import sys
import os
from langchain.vectorstores import Chroma
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from app.core.deps import llm, thinking_llm, embeddings, kis

from pydantic import BaseModel, Field
class StockDetailInfo(BaseModel):
    query: str = Field(description = "사용자의 입력된 쿼리 전체 텍스트")

class StockPreviousInfo(BaseModel):
    query: str = Field(description = "사용자의 입력된 쿼리 전체 텍스트")
    lengths: list = Field(description = "각 주식에 대한 조회 기간의 길이 (정수 꼴의 str을 원소로 가짐")
    periods: list = Field(description = "각 주식에 대한 기간 단위 (일이면 d, 주면 W, 월이면 M, 년이면 y)")

class StockOrderBook(BaseModel):
    query: str = Field(description = "사용자의 입력된 쿼리 전체 텍스트")


# 현재 파일의 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))
# backend 디렉토리 경로 (app의 부모 디렉토리)
backend_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
# 시스템 경로에 backend 디렉토리 
sys.path.insert(0, backend_dir)

from app.agents.module.module import TickerResolver


# 종목 티커 추론용 vector DB 로드
db_path = os.path.join(backend_dir, 'app', 'database', 'ticker_db')
ticker_db = Chroma(persist_directory=db_path, embedding_function=embeddings)

# 종목의 현재 정보를 가져오는 기능
@tool(args_schema = StockDetailInfo)
def stock_detail_info(query: str) -> str:
    """주식 종목에 대해 전일과 현재의 상세 정보를 가져옵니다.
    상세 정보는 크게 4가지로 이루어집니다.
    1. 종목 자체에 대한 정보 : 종목코드, 종목명, 시장, 업종정보
    2. 종목의 현재 가격에 대한 정보 : 현재가, 시장가, 고가, 저가, 환율, 거래량, 거래대금, 전일대비부호, 전일대비, 등락율
    3. 종목의 전일 가격에 대한 정보 : 전일종가, 전일거래량
    4. 종목의 실적에 대한 정보 : 52주 최고가, 52주 최저가, 52주 최고가 날짜, 52주 최저가 날짜, EPS, BPS, PER, PBR
    """
    ticker_resolver = TickerResolver(llm, ticker_db)

    names = ticker_resolver.extract_stock_names(query)
    tickers = []
    for nm in names:
        candidates = ticker_resolver.search_candidates(nm, 5)
        reranked_ticker = ticker_resolver.rerank_candidates(query, candidates)
        tickers.append(reranked_ticker)

    col_dict = {
        "symbol" : [],
        "name" : [],
        "market" : [],
        "sector_name" : [],
        "price" : [],
        "open" : [],
        "high" : [],
        "low" : [],
        "exchange_rate" : [],
        "volume" : [],
        "amount" : [],
        "sign" : [],
        "change" : [],
        "rate" : [],
        "prev_price" : [],
        "prev_volume" : [],
        "week52_high" : [],
        "week52_low" : [],
        "week52_high_date" : [],
        "week52_low_date" : [],
        "eps" : [],
        "bps" : [],
        "per" : [],
        "pbr" : [],
    }
    
    for ticker in tickers:
        stock = kis.stock(ticker)
        col_dict["symbol"].append(stock.quote().symbol)
        col_dict["name"].append(stock.quote().name) # 종목명
        col_dict["market"].append(stock.quote().market) # 종목시장
        col_dict["sector_name"].append(stock.quote().sector_name) # 업종명

        col_dict["price"].append(str(stock.quote().price)) # 현재가
        col_dict["open"].append(str(stock.quote().open)) # 당일시가
        col_dict["high"].append(str(stock.quote().high)) # 당일고가
        col_dict["low"].append(str(stock.quote().low)) # 당일저가
        col_dict["exchange_rate"].append(str(stock.quote().exchange_rate)) # 당일 환율
        col_dict["volume"].append(str(stock.quote().volume)) # 거래량
        col_dict["amount"].append(str(stock.quote().amount)) # 거래대금
        col_dict["sign"].append(stock.quote().sign) # 전일 대비부호
        col_dict["change"].append(str(stock.quote().change)) # 전일 대비
        col_dict["rate"].append(str(stock.quote().rate)) # 등락율

        col_dict["prev_price"].append(str(stock.quote().prev_price)) # 전일 종가
        col_dict["prev_volume"].append(str(stock.quote().prev_volume)) # 전일 거래량 

        col_dict["week52_high"].append(str(stock.quote().indicator.week52_high)) # 52주최고가
        col_dict["week52_low"].append(str(stock.quote().indicator.week52_low)) # 52주최저가
        col_dict["week52_high_date"].append(stock.quote().indicator.week52_high_date.strftime("%Y-%m-%d")) # 52주 최고가 날짜
        col_dict["week52_low_date"].append(stock.quote().indicator.week52_low_date.strftime("%Y-%m-%d")) # 52주 최저가 날짜

        col_dict["eps"].append(str(stock.quote().indicator.eps)) # EPS
        col_dict["bps"].append(str(stock.quote().indicator.bps)) # BPS 
        col_dict["per"].append(str(stock.quote().indicator.per)) # PER 
        col_dict["pbr"].append(str(stock.quote().indicator.pbr)) # PBR

    return {"raw_df" : col_dict}

# 종목의 과거 정보를 가져오는 기능 
@tool(args_schema = StockPreviousInfo)
def stock_previous_info(query:str, lengths:list, periods:list) -> str:
    """주식종목의 과거부터 오늘까지의 가격 정보를 하루 단위로 가져옵니다.
    전일과 오늘보다 더 과거 시점부터 종목의 가격정보가 필요할 때 사용합니다.
    """
    ticker_resolver = TickerResolver(llm, ticker_db)

    names = ticker_resolver.extract_stock_names(query)
    tickers = []
    for nm in names:
        candidates = ticker_resolver.search_candidates(nm, 5)
        reranked_ticker = ticker_resolver.rerank_candidates(query, candidates)
        tickers.append(reranked_ticker)

    return_dict = {}
    for i in range(len(tickers)):
        length_period = lengths[i]+periods[i]
        _dict = kis.stock(tickers[i]).chart(length_period).df()
        _dict['time'] = _dict['time'].apply(lambda x : str(x)[:10])
        return_dict[tickers[i]] = _dict.to_dict(orient = "list")
    
    return {"raw_df" : return_dict}
    
    
@tool(args_schema=StockOrderBook)
def get_orderbook_info(query: str) -> dict:
    """주식 호가 정보를 조회합니다."""
    
    ticker_resolver = TickerResolver(llm, ticker_db)
    names = ticker_resolver.extract_stock_names(query)
    if not names:
        return {"error": "종목명을 찾을 수 없습니다."}
    ticker = ticker_resolver.rerank_candidates(query, ticker_resolver.search_candidates(names[0], 5))
    ob = kis.stock(ticker).orderbook()
    return {
        "종목명": ob.name,
        "매수호가": ob.bid_price_list,
        "매수잔량": ob.bid_volumn_list,
        "매도호가": ob.ask_price_list,
        "매도잔량": ob.ask_volumn_list,
    }

@tool
def get_market_hours() -> dict:
    """장운영 시간 정보를 조회합니다."""
    hours = kis.market().hours()
    return {
        "현재시간": str(hours.now),
        "장상태": hours.status,
        "정규장시작": str(hours.open),
        "정규장종료": str(hours.close),
        "시간외시작": str(hours.after_open),
        "시간외종료": str(hours.after_close),
    }
    
    
    
def create_stock_info_agent():

    return create_react_agent(
        llm,
        tools = [stock_detail_info, stock_previous_info,get_orderbook_info,get_market_hours],
        name = "stock_info_agent",
        prompt = (
            "당신의 주식종목에 대한 정보를 제공하는 에이전트입니다."
            "주식종목의 현재 정보와 과거 정보를 조회할 수 있습니다."
        )
    )

# if __name__ == "__main__":
#     agent = create_stock_info_agent()
#     # question = "아이온큐 얼마야"
#     # for chunk in agent.stream(
#     #     {"messages" : [("human", question)]}, stream_mode = "values"
#     # ):
#     #     chunk["messages"][-1].pretty_print()