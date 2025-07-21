from langchain_core.language_models.chat_models import BaseChatModel
from langchain.vectorstores.base import VectorStore
from langchain.docstore.document import Document

from typing import List, Tuple

class TickerResolver:
    def __init__(self, llm: BaseChatModel, vector_db: VectorStore):
        """
        Parameters:
        - llm: An instance of a LangChain-compatible LLM (e.g., ChatOpenAI)
        - vector_db: A LangChain-compatible VectorStore (e.g., Chroma, FAISS)
        """
        self.llm = llm
        self.db = vector_db

    def extract_stock_names(self, query: str):
        alias_map = {
            "마소": "마이크로소프트",
            "넷플": "넷플릭스",
            "구글": "알파벳",
            "마스": "마이크로스트래티지",
            "스트레티지": "마이크로스트래티지",
            "아마존": "아마존닷컴",
            "페북": "메타"
        }

        alias_examples = "\n".join([f"- {k} → {v}" for k, v in alias_map.items()])

        prompt = f"""
        다음 문장에서 언급된 미국 주식 종목명을 정식 한글명으로 정규화해서 출력해줘.
        - 약칭, 별칭 포함해서 인식해.
        - 종목이 여러 개라면 쉼표(,)로 구분하고, 다른 설명은 절대 쓰지마.

        약칭 예시:
        {alias_examples}

        문장: "{query}"
        종목명:
        """

        response = self.llm.invoke(prompt)
        content = getattr(response, "content", None)
        if content is None or not isinstance(content, str):
            return []

        return [name.strip() for name in content.strip().split(",") if name.strip()]


    def search_candidates(self, name: str, top_k: int = 5) -> List[Tuple[Document, float]]:
        """
        Perform a similarity search on the vector DB using the stock name.
        Returns top-k documents with scores.
        """
        return self.db.similarity_search_with_score(name, k=top_k)

    def rerank_candidates(self, query: str, candidates: List[Tuple[Document, float]]) -> str:
        """
        Rerank top-k vector search candidates using LLM to pick the best ticker.
        """
        formatted = "\n".join([
            f"{i+1}. {doc.metadata['ticker']} ({doc.metadata['exchange']}): {doc.page_content}"
            for i, (doc, _) in enumerate(candidates)
        ])

        prompt = f"""
        사용자 질문: "{query}"

        아래 후보 종목 중 가장 적절한 '티커'만 대문자로 한 줄 출력해줘. 괄호, 설명 없이.

        Candidates:
        {formatted}
        """
        response = self.llm.invoke(prompt)
        return response.content.strip().upper()