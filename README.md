# HR RAG Chatbot (Agentic)

An HR chatbot that answers internal policy questions using RAG (Retrieval-Augmented Generation). It uses a Router LLM to decide whether a query needs policy context from the vector store, or can be answered directly. An Evaluator LLM then assesses the response quality.

## Features

- **Agentic Router**: Classifies queries as `needs_policy` (requiring RAG) or `general` (answered directly by LLM)
- **RAG Pipeline**: Uses LangChain + ChromaDB to retrieve relevant HR policy sections
- **Evaluator LLM**: Evaluates responses for relevance and faithfulness with structured output
- **CLI Interface**: Interactive command-line chat
- **Streamlit App** (optional): Web UI for easier interaction

## Tech Stack

- [LangChain](https://www.langchain.com/) - Framework for building LLM applications
- [ChromaDB](https://www.trychroma.com/) - Vector database for document storage/retrieval
- [Google Gemini](https://ai.google.dev/) - LLM provider (via `langchain-google-genai`)
- [LangChain Core](https://python.langchain.com/docs/core/) - Runnables, prompts, schemas
- [Pydantic v2](https://docs.pydantic.dev/) - Data validation/structured output

## Setup

### 1. Create environment variables

Copy `.env.example` to `.env` and add your Google Gemini API key:

```bash
cp .env.example .env
```

Then edit `.env`:
```
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=models/text-embedding-004
CHROMA_PERSIST_DIR=./chroma_db
HR_POLICIES_DIR=./data/hr_policies
```

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Ingest HR policy documents

This creates embeddings and stores them in ChromaDB:

```bash
python ingest.py
```

You should see output confirming documents were processed and stored.

### 4. Run the chatbot

**CLI version (recommended):**
```bash
python main.py
```

**Streamlit version (optional):**
```bash
streamlit run app.py
```

## Usage Examples

- "How many annual leave days do I get?" → Routed to RAG → Answers from leave policy
- "What is 2+2?" → Routed to direct LLM → "4"
- "Tell me about sick leave" → Routed to RAG
- "What's the weather like?" → Routed to direct (general query)

## Project Structure

```
HRChatbot/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── config.py           # Configuration and env loading
├── ingest.py           # Document ingestion into ChromaDB
├── main.py             # CLI chatbot
├── app.py              # Streamlit UI
├── src/
│   ├── __init__.py
│   ├── agent.py        # Main agent orchestrator (router → rag/direct → evaluator)
│   ├── evaluator.py    # Evaluator LLM for response quality
│   ├── llm.py          # LLM and embeddings factories
│   ├── rag.py          # RAG chain (retriever + prompt + LLM)
│   └── router.py       # Router LLM for query classification
├── data/
│   └── hr_policies/    # HR policy text documents
└── chroma_db/          # Vector store (created after ingestion)
```

## How it works

1. **Router**: An LLM classifies the user query into `needs_policy` or `general` based on whether it requires internal HR policy knowledge.
2. **Response Generation**: If `needs_policy`, retrieve relevant policy chunks from ChromaDB and generate an answer grounded in context. If `general`, answer directly with the LLM.
3. **Evaluator**: Another LLM evaluates the generated answer for relevance and faithfulness, returning scores and a verdict (PASS/FAIL).

## Customization

- Add more HR policy documents to `data/hr_policies/` (TXT or MD files), then re-run `ingest.py`.
- Adjust the routing/evaluation prompts in `src/router.py` and `src/evaluator.py`.
- Change the LLM model in `.env` (e.g., `gemini-2.5-pro`).

## Notes

- This project uses Google Gemini via `langchain-google-genai`. You'll need a valid API key.
- ChromaDB persists to disk in `chroma_db/`, so you only need to ingest once (or when documents change).
- The evaluator is included for demonstration of agentic evaluation; in production you might make it optional.
