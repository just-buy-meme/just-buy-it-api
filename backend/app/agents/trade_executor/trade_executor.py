from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
from pykis import KisAccount, KisOrder
from app.core.deps import llm, thinking_llm, embeddings, kis
from langchain.tools import tool
from app.agents.module.module import TickerResolver
from langchain.vectorstores import Chroma
import os


class StockBuyMarketPrice(BaseModel):
    query : str = Field(description = "사용자의 입력된 쿼리 전체 텍스트")
    qty : list = Field(description = "사용자가 시장가 매수를 원하는 수량 리스트. 수량은 'X주', 'X 주' 꼴로 입력되며, 그 중 'X'에 해당하는 값만 리스트로 받아야 합니다.")

class StockBuyChoicePrice(BaseModel):
    query : str = Field(description = "사용자의 입력된 쿼리 전체 텍스트")
    price : list = Field(description = "사용자가 지정가 매수를 원하는 가격 리스트")
    qty : list = Field(description = "사용자가 지정가 매수를 원하는 수량 리스트")

class StockSellMarketPrice(BaseModel):
    query : str =  Field(description = "사용자의 입력된 쿼리 전체 텍스트")
    qty : str = Field(description = "사용자가 시장가 매도를 원하는 수량")

class StockSellChoicePrice(BaseModel):
    query : str =  Field(description = "사용자의 입력된 쿼리 전체 텍스트")
    price : str = Field(description = "사용자가 지정가 매도를 원하는 가격")
    qty : str = Field(description = "사용자가 지정가 매도를 원하는 수량")


current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../../../"))
db_path = os.path.join(backend_dir, 'app', 'database', 'ticker_db')
ticker_db = Chroma(persist_directory=db_path, embedding_function=embeddings)

account: KisAccount = kis.account()



# 시장가 매수
@tool(args_schema = StockBuyMarketPrice)
def stock_buy_market_price(query : str, qty: list) -> str:
    """ 사용자의 쿼리로부터 시장가 매수하고 싶은 종목과 수량을 찾아 시장가 매수를 수행합니다.
    사용자의 쿼리에 가격이 명시되지 않았다면 시장가 매수를 원한다고 간주합니다.
    매수는 대개 '~사줘', '~매수해줘' 등의 쿼리로 유추합니다.
    """
    ticker_resolver = TickerResolver(llm, ticker_db)

    names = ticker_resolver.extract_stock_names(query)
    tickers = []
    for nm in names:
        candidates = ticker_resolver.search_candidates(nm, 5)
        reranked_ticker = ticker_resolver.rerank_candidates(query, candidates)
        tickers.append(reranked_ticker)

    for i in range(len(tickers)):
        stock = kis.stock(tickers[i])
        try :
            stock.buy(qty = qty[i])
            return f"{tickers[i]} {qty[i]}주를 시장가로 매수했습니다."
        except Exception as e:
            return f"다음의 에러로 시장가 매수를 수행하지 못했습니다 : {e}"

# 지정가 매수
@tool(args_schema = StockBuyChoicePrice)
def stock_buy_choice_price(query : str, price : list, qty: list) -> str:
    """ 사용자의 쿼리로부터 지정가 매수하고 싶은 종목과 가격, 수량을 찾아 지정가 매수를 수행합니다.
    사용자의 쿼리에 가격이 명시되어 있다면 지정가 매수를 원한다고 간주합니다.
    매수는 대개 '~사줘', '~매수해줘' 등의 쿼리로 유추합니다.
    """
    ticker_resolver = TickerResolver(llm, ticker_db)

    names = ticker_resolver.extract_stock_names(query)
    tickers = []
    for nm in names:
        candidates = ticker_resolver.search_candidates(nm, 5)
        reranked_ticker = ticker_resolver.rerank_candidates(query, candidates)
        tickers.append(reranked_ticker)

    for i in range(len(tickers)):
        stock = kis.stock(tickers[i])
        try :
            stock.buy(price = price[i], qty = qty[i])
            return f"{tickers[i]} {qty[i]}주를 {price[i]}로 지정가 매수했습니다."
        except Exception as e:
            return f"다음의 에러로 지정가 매수를 수행하지 못했습니다 : {e}"

# 시장가 매도
@tool(args_schema = StockSellMarketPrice)
def stock_sell_market_price(query : str, qty: list) -> str:
    """ 사용자의 쿼리로부터 시장가 매도하고 싶은 종목과 수량을 찾아 시장가 매도를 수행합니다.
    사용자의 쿼리에 가격이 명시되지 않았다면 시장가 매도를 원한다고 간주합니다.
    매도는 대개 '~팔아줘', '~매도해줘' 등의 쿼리로 유추합니다.
    """
    ticker_resolver = TickerResolver(llm, ticker_db)

    names = ticker_resolver.extract_stock_names(query)
    tickers = []
    for nm in names:
        candidates = ticker_resolver.search_candidates(nm, 5)
        reranked_ticker = ticker_resolver.rerank_candidates(query, candidates)
        tickers.append(reranked_ticker)

    for i in range(len(tickers)):
        stock = kis.stock(tickers[i])
        try :
            stock.sell(qty = qty[i])
            return f"{tickers[i]} {qty[i]}주를 시장가로 매도했습니다."
        except Exception as e:
            return f"다음의 에러로 시장가 매도를 수행하지 못했습니다 : {e}"

# 지정가 매도
@tool(args_schema = StockSellChoicePrice)
def stock_sell_choice_price(query : str, price : list, qty: list) -> str:
    """ 사용자의 쿼리로부터 지정가 매도하고 싶은 종목과 가격, 수량을 찾아 지정가 매도를 수행합니다.
    사용자의 쿼리에 가격이 명시되어 있다면 지정가 매도를 원한다고 간주합니다.
    매도는 대개 '~팔아줘', '~매도해줘' 등의 쿼리로 유추합니다.
    """
    ticker_resolver = TickerResolver(llm, ticker_db)

    names = ticker_resolver.extract_stock_names(query)
    tickers = []
    for nm in names:
        candidates = ticker_resolver.search_candidates(nm, 5)
        reranked_ticker = ticker_resolver.rerank_candidates(query, candidates)
        tickers.append(reranked_ticker)

    for i in range(len(tickers)):
        stock = kis.stock(tickers[i])
        try :
            stock.sell(price = price[i], qty = qty[i])
            return f"{tickers[i]} {qty[i]}주를 {price[i]}로 지정가 매도했습니다."
        except Exception as e:
            return f"다음의 에러로 지정가 매도를 수행하지 못했습니다 : {e}"

def create_trade_not_auto_agent():
    return create_react_agent(
        llm,
        tools = [stock_buy_market_price, stock_buy_choice_price, stock_sell_market_price, stock_sell_choice_price],
        name = "trade_not_auto_agent",
        prompt = (
            "당신은 시장가 매수 또는 지정가 매수 또는 시장가 매도 또는 지정가 매도를 수행하는 에이전트입니다."
            "사용자의 쿼리에서 다음의 정보를 파악하고 적절한 tool을 선택합니다." 
            "1. 매수를 원하는지 매도를 원하는지 유추합니다."
            "2. 시장가 매매를 원하는지 지정가 매매를 원하는지 유추합니다."
            "3. 매매를 원하는 종목, 가격 (지정가 매매시), 수량을 유추합니다."
        )
    )
