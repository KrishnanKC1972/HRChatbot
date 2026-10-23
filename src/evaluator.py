from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.llm import get_llm
from config import settings


class EvaluationResult(BaseModel):
    """Evaluation result for the generated answer."""
    
    relevance_score: float = Field(
        ge=0.0, le=1.0,
        description="Score from 0 to 1 indicating how relevant the answer is to the question."
    )
    faithfulness_score: float = Field(
        ge=0.0, le=1.0,
        description="Score from 0 to 1 indicating how grounded the answer is in the provided context. "
        "For answers not using context, score based on factual accuracy."
    )
    overall_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall quality score from 0 to 1."
    )
    verdict: str = Field(
        description="PASS if the answer is good quality, FAIL if it needs improvement."
    )
    reasoning: str = Field(
        description="Brief explanation of the evaluation."
    )
    suggestions: str = Field(
        description="Suggestions for improvement if verdict is FAIL, otherwise empty."
    )


def create_evaluator_chain():
    """Create evaluator LLM that assesses response quality."""
    llm = get_llm(temperature=0.1)
    structured_llm = llm.with_structured_output(EvaluationResult)
    
    prompt = ChatPromptTemplate.from_template(
        """You are an evaluator for an HR chatbot. Your task is to assess the quality of the 
        generated answer based on the question, the answer, and any context provided.
        
        Evaluate on these criteria:
        1. **Relevance** (0-1): Does the answer directly address the user's question?
        2. **Faithfulness** (0-1): Is the answer grounded in the provided context? If no context 
           was used (general query), assess factual correctness of the answer.
        3. **Overall** (0-1): Overall quality considering relevance and faithfulness.
        
        Return:
        - verdict: "PASS" if overall_score >= 0.7, otherwise "FAIL"
        - reasoning: Brief explanation of your assessment
        - suggestions: Specific suggestions for improvement if FAIL, else "None"
        
        Question: {question}
        
        Context (if any): {context}
        
        Answer: {answer}
        
        Evaluate carefully and provide objective scores."""
    )
    
    evaluator_chain = prompt | structured_llm
    return evaluator_chain


def evaluate_response(question: str, answer: str, context: str = "") -> EvaluationResult:
    """Evaluate the response quality."""
    chain = create_evaluator_chain()
    result = chain.invoke({
        "question": question,
        "context": context if context else "No context provided (direct answer)",
        "answer": answer
    })
    return result
