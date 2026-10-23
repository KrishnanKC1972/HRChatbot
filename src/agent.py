from src.router import route_query
from src.rag import get_rag_answer, get_rag_answer_with_sources, create_rag_chain
from src.evaluator import evaluate_response
from src.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# Phrases that indicate the assistant could not answer from the HR policies.
NOT_ANSWERED_MARKERS = (
    "i don't have enough information",
    "i do not have enough information",
    "insufficient information",
    "not enough information",
    "i couldn't find",
    "i could not find",
    "no relevant information",
    "knowledge base hasn't been ingested",
    "knowledge base has not been ingested",
    "error generating",
)


def detect_unanswered(answer: str) -> tuple[bool, str]:
    """Return (is_unanswered, reason) for a generated answer."""
    if not answer or not answer.strip():
        return True, "empty_answer"
    lowered = answer.lower()
    for marker in NOT_ANSWERED_MARKERS:
        if marker in lowered:
            if marker.startswith("error generating"):
                return True, "generation_error"
            if "ingested" in marker:
                return True, "knowledge_base_missing"
            return True, "no_policy_information"
    return False, ""


class HRAgent:
    """Agentic HR Chatbot that routes queries between RAG and direct LLM, then evaluates."""
    
    def __init__(self, evaluate: bool = True):
        self.evaluate = evaluate
        self.rag_chain = None
        # Lazy load rag chain
        try:
            self.rag_chain = create_rag_chain()
        except Exception:
            self.rag_chain = None

    def _rebuild_rag_chain(self):
        """Rebuild the RAG chain (e.g. after the ChromaDB collection was re-ingested)."""
        try:
            self.rag_chain = create_rag_chain()
        except Exception:
            self.rag_chain = None
        return self.rag_chain

    def _run_rag(self, query: str, with_sources: bool):
        """Run the RAG path, transparently recovering from a stale vector store handle."""
        last_error = None
        for attempt in range(2):
            try:
                chain = self.rag_chain if self.rag_chain is not None else self._rebuild_rag_chain()
                if with_sources:
                    answer, context, sources = get_rag_answer_with_sources(query, chain=chain)
                    return answer, context, sources
                answer, context = get_rag_answer(query, chain=chain)
                return answer, context, []
            except Exception as e:
                last_error = e
                # First failure may be a stale collection handle (e.g. server running while
                # `python ingest.py` recreated ChromaDB). Rebuild and retry once.
                self.rag_chain = None
        raise last_error
    
    def answer(self, query: str, with_sources: bool = False) -> dict:
        """
        Process a query through the agentic pipeline:
        1. Route: decide if needs RAG or direct LLM
        2. Generate: get answer via RAG or direct LLM
        3. Evaluate: assess answer quality (if enabled)
        
        Returns dict with answer, routing info, and evaluation.
        """
        result = {
            "query": query,
            "answer": "",
            "routing": {"needs_policy": False, "reasoning": ""},
            "context": "",
            "sources": [],
            "evaluation": None,
            "used_rag": False,
            "unanswered": False,
            "unanswered_reason": "",
        }
        
        # Step 1: Route the query
        try:
            classification = route_query(query)
            result["routing"]["needs_policy"] = classification.needs_policy
            result["routing"]["reasoning"] = classification.reasoning
        except Exception as e:
            # Fallback: route to RAG if error
            result["routing"]["needs_policy"] = True
            result["routing"]["reasoning"] = f"Router error, defaulting to RAG: {e}"
        
        # Step 2: Generate answer
        if result["routing"]["needs_policy"]:
            # Use RAG
            try:
                answer, context, sources = self._run_rag(query, with_sources)
                result["answer"] = answer
                result["context"] = context
                result["sources"] = sources
                result["used_rag"] = True
            except Exception as e:
                result["answer"] = f"Error generating RAG answer: {e}"
                result["context"] = ""
                result["used_rag"] = True
        else:
            # Use direct LLM
            try:
                llm = get_llm()
                direct_prompt = ChatPromptTemplate.from_template(
                    """You are a helpful assistant. Answer the user's question concisely and accurately.
                    
                    Question: {question}
                    
                    Answer:"""
                )
                direct_chain = direct_prompt | llm | StrOutputParser()
                answer = direct_chain.invoke({"question": query})
                result["answer"] = answer
                result["context"] = ""
                result["used_rag"] = False
            except Exception as e:
                result["answer"] = f"Error generating direct answer: {e}"
                result["context"] = ""
                result["used_rag"] = False
        
        # Step 3: Evaluate the answer
        if self.evaluate and result["answer"]:
            try:
                eval_result = evaluate_response(
                    question=query,
                    answer=result["answer"],
                    context=result["context"] if result["used_rag"] else ""
                )
                result["evaluation"] = {
                    "relevance_score": eval_result.relevance_score,
                    "faithfulness_score": eval_result.faithfulness_score,
                    "overall_score": eval_result.overall_score,
                    "verdict": eval_result.verdict,
                    "reasoning": eval_result.reasoning,
                    "suggestions": eval_result.suggestions,
                }
            except Exception as e:
                result["evaluation"] = {"error": f"Evaluation failed: {e}"}
        
        # Step 4: Flag answers that could not be grounded in the HR policies
        result["unanswered"], result["unanswered_reason"] = detect_unanswered(result["answer"])
        
        return result
