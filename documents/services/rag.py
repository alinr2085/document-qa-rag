"""RAG pipeline built with LangChain (LCEL):  retriever -> prompt -> LLM -> parser."""
import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .retrieval import get_retriever

NO_ANSWER = "در اسناد موجود اطلاعات مرتبطی با این پرسش پیدا نشد."

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a document question-answering assistant. Answer ONLY using the "
            "numbered context passages below. If the context does not contain the answer, "
            "say that the documents do not contain it - never invent facts. "
            "Reply in the same language as the question (Persian questions get Persian answers). "
            "Be concise and cite the passages you used like [1], [2].\n\nContext:\n{context}",
        ),
        ("human", "{question}"),
    ]
)

REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user's question as a short keyword-rich search query, in the same "
            "language. Output only the query.",
        ),
        ("human", "{question}"),
    ]
)


class LLMError(Exception):
    pass


def get_llm():
    if not settings.OPENROUTER_API_KEY:
        raise ImproperlyConfigured("OPENROUTER_API_KEY تنظیم نشده است (فایل .env را بررسی کنید).")
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        temperature=0,
        timeout=settings.LLM_TIMEOUT,
        max_retries=2,
    )


def search_documents(query: str, top_k: int | None = None):
    return get_retriever(top_k or settings.RAG_TOP_K).invoke(query)


def _format_context(docs) -> str:
    return "\n\n".join(
        f"[{i}] ({d.metadata['title']})\n{d.page_content}" for i, d in enumerate(docs, 1)
    )


def _sources(docs):
    return [
        {
            "document_id": d.metadata["document_id"],
            "title": d.metadata["title"],
            "chunk_index": d.metadata["chunk_index"],
            "score": d.metadata["score"],
            "snippet": d.page_content[:300],
        }
        for d in docs
    ]


def answer_question(question: str, top_k: int | None = None) -> dict:
    """Returns {answer, sources, model_name, response_time_ms}. Raises LLMError / ImproperlyConfigured."""
    started = time.monotonic()
    llm = None
    search_query = question

    if settings.RAG_QUERY_REWRITE:
        llm = get_llm()
        try:
            search_query = (REWRITE_PROMPT | llm | StrOutputParser()).invoke({"question": question}) or question
        except Exception:  # rewriting is optional; fall back to the original question
            search_query = question

    docs = search_documents(search_query, top_k)
    if not docs and search_query != question:
        docs = search_documents(question, top_k)

    if not docs:
        answer = NO_ANSWER
    else:
        llm = llm or get_llm()
        chain = ANSWER_PROMPT | llm | StrOutputParser()
        try:
            answer = chain.invoke({"context": _format_context(docs), "question": question})
        except Exception as exc:
            raise LLMError(f"خطا در ارتباط با مدل زبانی: {exc}") from exc

    return {
        "answer": answer.strip(),
        "sources": _sources(docs),
        "model_name": settings.OPENROUTER_MODEL,
        "response_time_ms": int((time.monotonic() - started) * 1000),
    }