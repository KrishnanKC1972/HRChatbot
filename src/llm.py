from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from config import settings

def get_llm(temperature: float = None, model: str = None) -> ChatGoogleGenerativeAI:
    """Create and return a ChatGoogleGenerativeAI LLM instance."""
    return ChatGoogleGenerativeAI(
        model=model or settings.gemini_model,
        temperature=temperature if temperature is not None else settings.temperature,
        google_api_key=settings.gemini_api_key,
    )

def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Create and return Google Generative AI embeddings."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.gemini_api_key,
    )
