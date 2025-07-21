import requests
from bs4 import BeautifulSoup
import re
import asyncio
from airflow.decorators import task
import time
from datetime import datetime
import logging
import os

urls = ['wallstreetbets/','Wallstreetbetsnew/','WallStreetbetsELITE/','stocks/','StockMarket/','investing/','options/']


url = "https://apewisdom.io/"
headers = {
    "User-Agent": "Mozilla/5.0"
}
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s'
)
@task
def api_parser(url):
    url_base = os.path.basename(url)
    data= {}
    tickers = []
    logging.info(f"? [{datetime.now()}]")
    response = requests.get(url, headers=headers)
    html_content = response.text 
    soup_base = BeautifulSoup(html_content, "html.parser")
    print(time.time())
    i =0
    for link in soup_base.find_all('a', href=True):
        href = link['href']

        if href.startswith("/stocks/"):
            match = re.match(r"^/stocks/([^/]+)/?", href)
            if match:
                i+=1
            
                data= {}
                ticker = match.group(1)
            
                url_ticker = f"https://apewisdom.io/stocks/{ticker}"
                data['url_base'] = url_base
                data['id'] = i
                data['ticker'] = ticker
        
                re_ticker = requests.get(url_ticker,headers=headers)
                soup_ticker = BeautifulSoup(re_ticker.text, "html.parser")
                tiles = soup_ticker.find_all("div", class_="details-small-tile")
                for tile in tiles:
                    title = tile.find("div", class_="tile-title")
            
                    value_div = tile.find("div", class_="tile-value")
                    data[title.text.strip()] = value_div.text.strip().replace('  ',' ').replace(' ',',')

              
                # data['mention'] =  mentions_api(soup_ticker)
                # data['upvote'] = upvotes_api(soup_ticker)
                # data['user'] = users_api(soup_ticker)
                # data['sentiment'] = sentiments_api(soup_ticker)
                
            print(data)
            tickers.append(data)
    return tickers

                        
                

   
  
def mentions_api(soup_ticker):              
                
    mentions_tag = soup_ticker.find(text="Mentions")
    if mentions_tag:
        men ={}
        mentions = mentions_tag.find_next().text.strip()
    
    return mentions
            
def upvotes_api(soup_ticker):
    
    upvotes_tag = soup_ticker.find(text="Upvotes")
    if upvotes_tag:
        upvotes = upvotes_tag.find_next().text.strip()

    return upvotes

def users_api(soup_ticker):
            
    users_tag = soup_ticker.find(text=re.compile("mentioning users", re.I))
    if users_tag:
       
        users = users_tag.find_next().text.strip()
    return users

def sentiments_api(soup_ticker):
    
        
    sentiment_tag = soup_ticker.find(text="Sentiment")
    if sentiment_tag:
    
        sentiment_value = sentiment_tag.find_next().text.strip()
    return sentiment_value

        
# asyncio.run(main())
#if __name__ == '__main__':
    
#     scheduler = BlockingScheduler()
#     scheduler.add_job(api_parser, 'interval', seconds=10,start_date=datetime.now()) 
#     scheduler.start()

   
    # try:
    #     while True:
    #         time.sleep(1)
    # except (KeyboardInterrupt, SystemExit):
    #     scheduler.shutdown()