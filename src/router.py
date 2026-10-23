from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field
from src.llm import get_llm
from config import settings


class QueryClassification(BaseModel):
    """Classification of whether a query needs HR policy context (RAG) or can be answered directly."""
    
    needs_policy: bool = Field(
        description="True if the query requires internal HR policy knowledge to answer accurately. "
        "False if it can be answered with general knowledge or is a casual conversation."
    )
    reasoning: str = Field(
        description="Brief explanation for the classification decision."
    )


def create_router_chain():
    """Create router LLM that decides whether to use RAG or direct LLM."""
    llm = get_llm(temperature=0.1)  # Lower temperature for classification
    structured_llm = llm.with_structured_output(QueryClassification)
    
    prompt = ChatPromptTemplate.from_template(
        """You are a router for an HR chatbot. Your task is to decide whether the user's query 
        requires access to internal HR policies (leave, benefits, working hours, code of conduct, 
        IT security, expenses, etc.) or can be answered directly with general knowledge.
        
        Classify as NEEDS_POLICY (true) if the query is about:
        - Leave policies (annual leave, sick leave, parental leave)
        - Working hours, overtime, remote work
        - Benefits (health insurance, retirement, development budget)
        - Code of conduct, harassment, confidentiality
        - IT security, passwords, devices, data protection
        - Expense policies, travel, reimbursements
        - Internal company procedures related to HR
        
        Classify as GENERAL (false) if the query is:
        - Greetings, small talk ("hi", "hello", "how are you")
        - General knowledge questions (math, definitions, facts unrelated to company policies)
        - Casual conversation
        - Questions that don't reference specific company HR rules
        
        Be conservative - if uncertain, and it sounds like it could relate to company policies, 
        classify as needs_policy (true).
        
        User query: {query}
        
        Return your classification."""
    )
    
    router_chain = prompt | structured_llm
    return router_chain


def route_query(query: str) -> QueryClassification:
    """Route the query and return classification."""
    chain = create_router_chain()
    result = chain.invoke({"query": query})
    return result
