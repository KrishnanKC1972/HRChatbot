import streamlit as st
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent import HRAgent
from src.rag import load_vector_store

st.set_page_config(
    page_title="HR Policy Assistant | Agentic RAG Chatbot",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional colorful UI
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1507679799987-c73779587ccf?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(15,23,42,0.75) 0%, rgba(30,58,138,0.65) 100%);
        z-index: 0;
    }
    .main .block-container {
        position: relative;
        z-index: 1;
    }
    
    /* Header gradient card */
    .header-card {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #3b82f6 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.25);
        margin-bottom: 1.5rem;
    }
    
    .header-title {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }
    
    .header-subtitle {
        color: #bfdbfe;
        font-size: 0.95rem;
        margin: 0.4rem 0 0 0;
        font-weight: 400;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.95) 100%); backdrop-filter: blur(8px));
    }
    
    [data-testid="stSidebar"] * {
        color: #e2e8f0;
    }
    
    [data-testid="stSidebar"] h2 {
        color: #ffffff;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    [data-testid="stSidebar"] h3 {
        color: #f1f5f9;
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
    }
    
    /* Chat container */
    .stChat {
        background: #ffffff;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04);
        border: 1px solid #e2e8f0;
    }
    
    /* User message bubble */
    [data-testid="stChatMessageContent"]:has(div.user-message) {
        background: linear-gradient(90deg, #dbeafe 0%, #eff6ff 100%);
        border-left: 4px solid #2563eb;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-left: 2rem;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.1);
    }
    
    /* Assistant message bubble */
    [data-testid="stChatMessageContent"]:has(div.assistant-message) {
        background: linear-gradient(90deg, #dcfce7 0%, #f0fdf4 100%);
        border-left: 4px solid #16a34a;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-right: 2rem;
        box-shadow: 0 1px 2px rgba(22, 163, 74, 0.1);
    }
    
    /* Agent details expander */
    .streamlit-expanderHeader {
        background-color: #f8fafc !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        color: #475569 !important;
    }
    
    .streamlit-expanderContent {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }
    
    /* Metric badges */
    .metric-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
    
    .badge-rag {
        background-color: #dbeafe;
        color: #1e40af;
    }
    
    .badge-direct {
        background-color: #dcfce7;
        color: #166534;
    }
    
    .badge-pass {
        background-color: #dcfce7;
        color: #166534;
    }
    
    .badge-fail {
        background-color: #fee2e2;
        color: #991b1b;
    }
    
    /* Divider styling */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #cbd5e1, transparent);
        margin: 1rem 0;
    }
    
    /* Examples list */
    .example-item {
        background: rgba(148, 163, 184, 0.15);
        padding: 0.5rem 0.7rem;
        border-radius: 6px;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
        border-left: 2px solid #64748b;
    }
    
    /* Status success/warning/error */
    .stSuccess, .stWarning, .stError {
        border-radius: 8px;
        padding: 0.7rem 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header-card">
    <h1 class="header-title">🏢 HR Policy Assistant</h1>
    <p class="header-subtitle">Agentic RAG • Intelligent Query Routing • Automated Response Evaluation</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    evaluate = st.checkbox("Enable Response Evaluator", value=True, 
                           help="Automatically assess response quality for relevance & faithfulness")
    
    st.markdown("---")
    
    st.markdown("## 💡 Example Queries")
    st.markdown('<div class="example-item">"How many annual leave days do I get?"</div>', unsafe_allow_html=True)
    st.markdown('<div class="example-item">"What is the sick leave policy?"</div>', unsafe_allow_html=True)
    st.markdown('<div class="example-item">"Can I work remotely?"</div>', unsafe_allow_html=True)
    st.markdown('<div class="example-item">"Tell me about health benefits"</div>', unsafe_allow_html=True)
    st.markdown('<div class="example-item">"What is 2+2?"</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("## 📊 Knowledge Base Status")
    try:
        load_vector_store()
        st.success("✅ Vector Store Loaded")
        st.caption("HR policy documents are ready for retrieval")
    except FileNotFoundError:
        st.warning("⚠️ Vector Store Not Found")
        st.caption("Run `python ingest.py` to build the knowledge base")
    except Exception as e:
        st.error("❌ Connection Error")
        st.caption(f"{e}")

# Initialize agent
@st.cache_resource
def get_agent(evaluate_flag):
    return HRAgent(evaluate=evaluate_flag)

agent = get_agent(evaluate)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
            if "metadata" in message:
                with st.expander("🔍 Agent Analysis & Evaluation"):
                    metadata = message["metadata"]
                    
                    # Routing info
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Query Routing**")
                        route_type = metadata["route"]
                        if "RAG" in route_type:
                            st.markdown(f'<span class="metric-badge badge-rag">📚 {route_type}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="metric-badge badge-direct">💡 {route_type}</span>', unsafe_allow_html=True)
                        st.caption(f"Needs Policy: {metadata['needs_policy']}")
                    
                    with col2:
                        st.markdown("**Routing Reasoning**")
                        st.write(metadata["reasoning"])
                    
                    st.divider()
                    
                    # Evaluation info
                    if "evaluation" in metadata:
                        eval_info = metadata["evaluation"]
                        e1, e2, e3 = st.columns(3)
                        with e1:
                            st.metric("Relevance", eval_info["relevance"])
                        with e2:
                            st.metric("Faithfulness", eval_info["faithfulness"])
                        with e3:
                            st.metric("Overall", eval_info["overall"])
                        
                        verdict = eval_info["verdict"]
                        if verdict == "PASS":
                            st.markdown(f'<span class="metric-badge badge-pass">✅ {verdict}</span>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<span class="metric-badge badge-fail">⚠️ {verdict}</span>', unsafe_allow_html=True)
                        st.caption(f"Verdict based on overall score ≥ 0.7")

# User input
if prompt := st.chat_input("Ask me anything about HR policies..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f'<div class="user-message">{prompt}</div>', unsafe_allow_html=True)
    
    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("🧠 Analyzing query & generating response..."):
            result = agent.answer(prompt)
        
        st.markdown(f'<div class="assistant-message">{result["answer"]}</div>', unsafe_allow_html=True)
        
        # Show metadata
        metadata = {
            "used_rag": result["used_rag"],
            "route": "RAG (Policy Retrieval)" if result["used_rag"] else "Direct LLM",
            "needs_policy": result["routing"]["needs_policy"],
            "reasoning": result["routing"]["reasoning"],
        }
        if result.get("evaluation"):
            eval_info = result["evaluation"]
            if "error" not in eval_info:
                metadata["evaluation"] = {
                    "verdict": eval_info["verdict"],
                    "relevance": f"{eval_info['relevance_score']:.2f}",
                    "faithfulness": f"{eval_info['faithfulness_score']:.2f}",
                    "overall": f"{eval_info['overall_score']:.2f}",
                }
        
        with st.expander("🔍 Agent Analysis & Evaluation"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Query Routing**")
                route_type = metadata["route"]
                if "RAG" in route_type:
                    st.markdown(f'<span class="metric-badge badge-rag">📚 {route_type}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="metric-badge badge-direct">💡 {route_type}</span>', unsafe_allow_html=True)
                st.caption(f"Needs Policy: {metadata['needs_policy']}")
            
            with col2:
                st.markdown("**Routing Reasoning**")
                st.write(metadata["reasoning"])
            
            st.divider()
            
            if "evaluation" in metadata:
                eval_info = metadata["evaluation"]
                e1, e2, e3 = st.columns(3)
                with e1:
                    st.metric("Relevance", eval_info["relevance"])
                with e2:
                    st.metric("Faithfulness", eval_info["faithfulness"])
                with e3:
                    st.metric("Overall", eval_info["overall"])
                
                verdict = eval_info["verdict"]
                if verdict == "PASS":
                    st.markdown(f'<span class="metric-badge badge-pass">✅ {verdict}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="metric-badge badge-fail">⚠️ {verdict}</span>', unsafe_allow_html=True)
                st.caption("Verdict: PASS if Overall ≥ 0.7")
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "metadata": metadata
    })
