from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from src.llm import get_embeddings, get_llm
from config import settings
import os


def load_vector_store():
    """Load existing vector store from disk."""
    if not os.path.exists(settings.chroma_persist_dir):
        raise FileNotFoundError(
            f"ChromaDB not found at {settings.chroma_persist_dir}. "
            f"Please run ingest.py first to create the vector store."
        )
    
    embeddings = get_embeddings()
    vector_store = Chroma(
        persist_directory=settings.chroma_persist_dir,
        embedding_function=embeddings,
    )
    return vector_store


def format_docs(docs):
    """Format retrieved documents into a single string."""
    return "\n\n---\n\n".join([doc.page_content for doc in docs])


def create_rag_chain():
    """Create a RAG chain that retrieves relevant documents and generates answers."""
    try:
        vector_store = load_vector_store()
    except FileNotFoundError:
        # Return a fallback chain if vector store doesn't exist
        llm = get_llm()
        fallback_prompt = ChatPromptTemplate.from_template(
            """You are an HR assistant. The vector store with HR policies is not available yet.
            Please inform the user to run 'python ingest.py' to build the knowledge base.
            
            User question: {question}
            
            Response: The HR knowledge base hasn't been ingested yet. Please run 'python ingest.py' 
            to load the policy documents into the vector store."""
        )
        return fallback_prompt | llm | StrOutputParser()
    
    retriever = vector_store.as_retriever(search_kwargs={"k": settings.retrieval_k})
    llm = get_llm()
    
    prompt = ChatPromptTemplate.from_template(
        """You are a helpful HR assistant. Your job is to answer questions about internal HR policies 
        based ONLY on the provided policy context.
        
        Use the following context to answer the question. If the context does not contain sufficient 
        information to answer the question, say "I don't have enough information in the HR policies 
        to answer this question." Do not make up facts or use prior knowledge.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:"""
    )
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain


def get_rag_answer(query: str, chain=None) -> tuple[str, str]:
    """
    Get answer using RAG. Returns (answer, retrieved_context).
    If chain not provided, creates one.
    """
    if chain is None:
        chain = create_rag_chain()
    
    # For retrieval context, we need to run retriever separately
    try:
        vector_store = load_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": settings.retrieval_k})
        docs = retriever.invoke(query)
        context = format_docs(docs)
    except Exception:
        context = ""
    
    answer = chain.invoke(query)
    return answer, context


def get_rag_answer_with_sources(query: str, chain=None) -> tuple[str, str, list[dict]]:
    """
    Get answer using RAG plus the retrieved source documents.
    Returns (answer, retrieved_context, sources) where sources is a list of
    {source, page, snippet} dicts usable by a UI to show which policies were used.
    """
    if chain is None:
        chain = create_rag_chain()

    sources: list[dict] = []
    context = ""
    try:
        vector_store = load_vector_store()
        retriever = vector_store.as_retriever(search_kwargs={"k": settings.retrieval_k})
        docs = retriever.invoke(query)
        context = format_docs(docs)
        for doc in docs:
            content = doc.page_content or ""
            sources.append({
                "source": os.path.basename(doc.metadata.get("source", "")) or "unknown",
                "page": doc.metadata.get("page"),
                "snippet": content[:300].strip(),
            })
    except Exception:
        context = ""

    answer = chain.invoke(query)
    return answer, context, sources
