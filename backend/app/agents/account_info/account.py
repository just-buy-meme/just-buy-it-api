from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
import os
from langchain_core.tools import tool
from app.core.deps import llm, thinking_llm, embeddings, kis

from pykis import PyKis, KisAccount, KisBalance, KisOrderProfits, KisDailyOrders, KisBalanceStock
from datetime import datetime, date


class user_profits(BaseModel):
    date:str = Field(default='',description='get_user_profits args')
    
class daily_orders(BaseModel):
    
    start_date : str = Field(default='',description='get_user_daily_orders args')
    end_date : str = Field(default='')

class buy_orders(BaseModel):
    
    ticker : str = Field(default='',description='buy_orders args')
    

account: KisAccount = kis.account()

@tool
def get_user_account_balance() -> float:
    """계좌 정보를 조회한다."""

    balance: KisBalance = account.balance()
    # print('get_user_account_balance', user_id)
    return balance


@tool
def get_user_profits(user:user_profits):
    "특정 기간의 손익을 조회한다."
    print(user.date)

    d = datetime.strptime(user.date,"%Y%m%d").date()
    profits = KisOrderProfits = account.profits(start=d)
    
    return profits
    
@tool
def get_user_daily_orders(user:daily_orders):
    "일별 체결 내역을 조회한다."
    start_date = datetime.strptime(user.start_date,"%Y%m%d").date()
    end_date = datetime.strptime(user.end_date,"%Y%m%d").date()
    daily_orders: KisDailyOrders = account.daily_orders(start=start_date, end=end_date)
    
    return daily_orders

    
# @tool
# def get_user_stock_balance(user_id: str) -> float:
#     """Get user's stock balance"""
#     return ("삼성전자", 10)
    


def create_account_info_agent():
    return create_react_agent(
        llm,
        tools=[get_user_account_balance, get_user_profits,get_user_daily_orders],
        name="account_info_agent",
        prompt=(
            "당신은 사용자의 계좌와 관련된 정보를 제공하는 에이전트입니다."
            "사용자의 계좌 정보를 알고싶을 때, get_user_account_balance를 사용하세요."
            "특정 기간의 이익률을 알고싶을 때, get_user_profits을 사용하세요."
            "특정 기간의 일별 체결 했는지를 알고싶을 떄, get_user_daily_order를 사용하세요."
        )
    )

# if __name__ == "__main__":
#     agent = create_account_info_agent()
#     recent_user_id = "1234567890"

#     question = "2024년 5월 2일 손익 알려줘"
#     # question = question + f" 사용자 아이디는 {recent_user_id} 입니다."
   
#     for chunk in agent.stream(
#         {"messages": [("human", question)]}, stream_mode="values"
#     ):
#         chunk["messages"][-1].pretty_print()