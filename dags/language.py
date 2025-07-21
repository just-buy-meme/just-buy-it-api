from langchain_ollama.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from app.agents.configure import llm

query = {'id': 70, 'ticker': 'WMT', 'Mentions': '8,-11%', 'Upvotes': '22,+29%', 'mentioning users': '9', 'Sentiment': '33%'}


def transform_sentence(query):
    
    def prompt_rethink(query):
        sentence=""

        for key in query.keys():
            value = query[key]
            sentence += str(key) + ' ' + str(value) 
        return {'query':sentence}
    prompt_text = """You are a good investor. You have to write this word converting to the sentence. 
                There are traits about the stocks. id represents the meme stock ranking, and a value means the stock is ranked value in attention. 
                The ticker is the stock symbol.
                Also, Mentions have two parts: before the comma indicates the number of mentions, and after the comma indicates the percentage change in mentions over previous days. 
                Upvotes follow a similar pattern. 
                Mentioning users indicate the number of distinct users who mentioned the stock. 
                Sentiment is the overall sentiment score for the ticker. 
                So, you have to write a full sentence summarizing this query.
                [additional Instructions]
                - Don't contain the additional sentence except stock.
                
                Here is the query:
                {query}
                """
    prompt = ChatPromptTemplate.from_template(prompt_text)

    #llm = ChatOllama(model='llama3.2:latest',base_url="http://app:11434")

    chain = RunnableLambda(prompt_rethink) | prompt | llm | StrOutputParser()
    response = chain.invoke(query)
    return response

    
