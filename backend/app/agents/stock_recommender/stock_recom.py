from langchain_core.documents import Document
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.tools import tool
from langchain_core.output_parsers import StrOutputParser
import psycopg2
import json
import asyncio
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
import os
from langchain_openai import ChatOpenAI

class State(BaseModel):

    content:str =Field(default='')


from app.core.deps import llm, thinking_llm, embeddings, kis

conn = psycopg2.connect(
dbname="app",
user="postgres",
password="lZVKzhTKsPSklN2KmTpPX26oA_ExvBOV35MF9AyOUJA",
host="postgres",
port="5432") 
cur = conn.cursor()
    

cur.execute("""
            CREATE TABLE IF NOT EXISTS db_crawl4
            (   
                start_time TIMESTAMPTZ,
                url_base TEXT,
                id INTEGER,
                ticker TEXT,
                mentions INTEGER,
                mentions_percent TEXT,
                upvote INTEGER,
                upvote_percent TEXT,
                users INTEGER,
                users_percent TEXT,
                sentiment TEXT
                
            );
            """)

query = "SELECT * FROM db_crawl4;"
df = pd.read_sql(query, conn)
df = pd.DataFrame(df)
# embedding = HuggingFaceEmbeddings(model_name='sentence-transformers/all-mpnet-base-v2')

prompt_text = """ You are a best investor like warren buffet. You have to recommend the stock to refer the question and table.
                First table has a 10 columns including "start_time", "url_base", "id", "ticker", "mentions","mentions_percent", "upvote","upvote_percent","users", "users_percent","sentiment".
                
                1. "start_time" is the related to the when to crawl the data.
                1. "url_base" is the related to the where to crawling. There are four transform_bets, transform_new, transform_Elite, transform_bets. It is the string type.
                2. "id" is related to the order of the meme score. The highest is the 1 and the lowest is the 100.
                3. "ticker" is the stock name. 
                4. "mentions" refers to the number of times the ticker was mentioned on that day.
                5. "mentions_percent" indicates the percentage change in mentions compared to 24 hours earlier. It is the Text format and it indicates the percentage. some tickers does not have this metrics.
                6. "upvote" is a metric that reflects how much interest people have in the ticker.
                7. "upvote_percent" shows how much the level of interest has changed compared to 24 hours ago. It is the Text format and it indicates the percentage. some tickers does not have this metrics.
                8. "users" refers to the number of unique users who mentioned the ticker.
                9. "users_percent" represents the change in the number of users over the past 24 hours. It is the Text format and it indicates the percentage. some tickers does not have this metrics.
                10. "sentiment" indicates whether people feel positively or negatively about the ticker. It is the text format includes %. It ranges from 0 to 100.
                
                You have to recommend the ticker and why you choose it. 
                Here is the question:
                {question}
                
                Here is the table:
                {table}
"""         
prompt = ChatPromptTemplate.from_template(prompt_text)

prompt_text2 = """ You are a good recommendation and best investor.
                You have to respond why you select this ticker and why do you recommend refer to the query.
                
                Here is the query:
                {query}
                Here is the ticker:
                {ticker}
"""
def find_upper_iqr_outliers(df, column):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    upper_bound = Q3 + 1.5 * IQR

    outliers = df[df[column] > upper_bound]
    return outliers

def mention_outliers(df):
    mentions_high_outliers = find_upper_iqr_outliers(df, 'mentions')
    unique_outliers = mentions_high_outliers.drop_duplicates(subset='ticker')
    return unique_outliers
    
def upvotes_outliers(df):
    
    upvotes_high_outliers = find_upper_iqr_outliers(df, 'upvote')
    unique_outliers = upvotes_high_outliers.drop_duplicates(subset='ticker')
    return unique_outliers

def users_outliers(df): 
    users_high_outliers = find_upper_iqr_outliers(df, 'users')
    unique_outliers = users_high_outliers.drop_duplicates(subset='ticker')
    return unique_outliers

# combined_outliers = pd.concat([mentions_high_outliers, upvotes_high_outliers, users_high_outliers])
# unique_outliers = combined_outliers.drop_duplicates(subset='ticker')

prompt2 = ChatPromptTemplate.from_template(prompt_text2)
async def RAG_system(state:State):
    if "멘션" in state.content:
        unique_outliers = mention_outliers(df)
    elif "좋아요" in state.content:
        unique_outliers = upvotes_outliers(df)
    elif "언급" in state.content:
        unique_outliers = users_outliers(df)
    else:
        unique_outliers = mention_outliers(df)

    chain = {'question':RunnablePassthrough(),'table':RunnablePassthrough()} | prompt | llm | StrOutputParser()
    
    response = await chain.ainvoke({'question':state.content,'table':unique_outliers.to_string()})
    return {"content": response}



def create_stock_recommender_agent():
    graph_state = StateGraph(State)
    graph_state.add_node("RAG",RAG_system)
    graph_state.set_entry_point("RAG")
    graph = graph_state.compile()
    return graph