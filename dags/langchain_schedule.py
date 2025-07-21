from airflow import DAG
from airflow.operators.python import PythonOperator, get_current_context
from airflow.decorators import task
from datetime import datetime,timedelta
from crawl import api_parser
import psycopg2
import os
import numpy as np
from langchain.schema import Document
from datetime import datetime
from dotenv import load_dotenv


urls =['wallstreetbets','Wallstreetbetsnew','WallStreetbetsELITE','stocks','StockMarket','investing','options']

load_dotenv()
url = "https://apewisdom.io/"
# embedding = HuggingFaceEmbeddings(model_name='sentence-transformers/all-mpnet-base-v2')

user= "postgres"
db = "app"
PASSWORD ="lZVKzhTKsPSklN2KmTpPX26oA_ExvBOV35MF9AyOUJA"
conn = psycopg2.connect(
    dbname=db,
    user=user,
    password=PASSWORD,
    host="postgres",
    port="5432"
)

@task
def transformation(task_i):
    context = get_current_context()
    data = context["ti"].xcom_pull(task_ids=task_i,key="return_value")


    embeddings= []
 
    for i in range(1,len(data)):
        
        if ',' in data[i]['Mentions']:
            if len(data[i]['Mentions'].split(',')) ==2:
                data[i]['Mentions_percent'] = data[i]['Mentions'].split(',')[1] 
            else:
                data[i]['Mentions_percent'] = None

            data[i]['Mentions'] = int(data[i]['Mentions'].split(',')[0])
        else:
            data[i]['Mentions_percent'] = None


        if ',' in data[i]['Upvotes']:
            if len(data[i]['Upvotes'].split(',')) == 2:
                data[i]['Upvotes_percent'] = data[i]['Upvotes'].split(',')[1]
            else:
                data[i]['Upvotes_percent'] = None
            data[i]['Upvotes'] = int(data[i]['Upvotes'].split(',')[0])

        else:
            data[i]['Upvotes_percent'] = None
        
        if ',' in data[i]['mentioning users']:
            if len(data[i]['mentioning users'].split(',')) == 2:
                data[i]['mentioning_users_percent'] =  data[i]['mentioning users'].split(',')[1]
            else:
                data[i]['mentioning_users_percent'] = None

            data[i]['mentioning users'] = int(data[i]['mentioning users'].split(',')[0])
        else:
            data[i]['mentioning_users_percent'] = None
        
    return data
    
    
@task
def database_load(task_i):
    context = get_current_context()
    data = context['ti'].xcom_pull(task_ids=task_i,key="return_value")
    start_time = context['dag_run'].start_date
    print(start_time)
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
    for i in range(1,len(data)):
      
        cur.execute("""INSERT INTO db_crawl4 (start_time, url_base, id, ticker, mentions, mentions_percent, upvote, upvote_percent, users, users_percent, sentiment) 
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (start_time,data[i]['url_base'],i,data[i]['ticker'],data[i]['Mentions'],data[i]['Mentions_percent'], data[i]['Upvotes'], data[i]['Upvotes_percent'],data[i]['mentioning users'],data[i]['mentioning_users_percent'],data[i]['Sentiment']))
        conn.commit()
    cur.close()
    conn.close()
    

with DAG(
    dag_id ="scheduler_crawling",
    schedule_interval=timedelta(minutes=15),  
    start_date=datetime(2024, 1, 1),
    catchup=False,  
    tags=['crawl2']
) as dag:
    

    task_bets = api_parser.override(task_id="crawling_bets")(os.path.join(url, urls[0]))  
    task_new = api_parser.override(task_id="crawling_new")(os.path.join(url, urls[1]))  
    task_Elite = api_parser.override(task_id="crawling_Elite")(os.path.join(url, urls[2]))  
    task_stocks = api_parser.override(task_id="crawling_stocks")(os.path.join(url, urls[3]))  
    
    
    transform_bets = transformation.override(task_id="transform_bets")("crawling_bets")
    transform_new = transformation.override(task_id="transform_new")("crawling_new")
    transform_Elite = transformation.override(task_id="transform_Elite")("crawling_Elite")
    transform_stocks = transformation.override(task_id="transform_stocks")("crawling_stocks")

    load_bets = database_load.override(task_id="load_bets")("transform_bets")
    load_new = database_load.override(task_id="load_new")("transform_new")
    load_Elite = database_load.override(task_id="load_Elite")("transform_Elite")
    load_stocks = database_load.override(task_id="load_stocks")("transform_stocks")

    
    task_new >> transform_new >> load_new
    
    task_Elite >> transform_Elite >> load_Elite
    
    task_bets >> transform_bets >> load_bets
    
    task_stocks >> transform_stocks >> load_stocks

