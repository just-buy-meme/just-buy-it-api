from pykis import PyKis
from langchain_openai import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings

from app.core.config import settings


llm = ChatOpenAI(
    model_name=settings.OPENROUTER_MODEL_NAME,
    openai_api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_ENDPOINT
)

thinking_llm = ChatOpenAI(
    model_name=settings.OPENROUTER_THINKING_MODEL_NAME,
    openai_api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_ENDPOINT
)

embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

kis = PyKis(
   id=settings.KIS_ID,
   account=settings.KIS_ACCOUNT,
   appkey=settings.KIS_APPKEY,
   secretkey=settings.KIS_SECRETKEY,
   virtual_id=settings.KIS_VIRTUAL_ID,
   virtual_appkey=settings.KIS_VIRTUAL_APPKEY,
   virtual_secretkey=settings.KIS_VIRTUAL_SECRETKEY,
   keep_token=True,
) 