from src.agent import HRAgent
from src.rag import load_vector_store
import sys

def print_separator():
    print("-" * 60)

def main():
    print("HR RAG Chatbot (Agentic)")
    print_separator()
    
    # Check if vector store exists
    try:
        load_vector_store()
        print("[OK] Vector store loaded successfully")
    except FileNotFoundError:
        print("[WARN] Vector store not found!")
        print("  Run 'python ingest.py' first to build the knowledge base.")
        print_separator()
        choice = input("Continue anyway? (y/n): ").strip().lower()
        if choice != 'y':
            sys.exit(0)
    except Exception as e:
        print(f"[WARN] Warning: {e}")
    
    print_separator()
    print("Commands:")
    print("  - Type your question to chat")
    print("  - Type 'help' for examples")
    print("  - Type 'exit' or 'quit' to end")
    print_separator()
    
    agent = HRAgent(evaluate=True)
    
    while True:
        try:
            query = input("\n💬 You: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ('exit', 'quit', 'q'):
                print("Goodbye! 👋")
                break
            elif query.lower() == 'help':
                print("\nExample questions:")
                print("  - 'How many annual leave days do I get?'")
                print("  - 'What is the sick leave policy?'")
                print("  - 'Can I work remotely?'")
                print("  - 'What is the password policy?'")
                print("  - 'What is 2+2?' (general query)")
                print("  - 'Tell me a joke' (general query)")
                continue
            
            print("\n🤖 Thinking...")
            result = agent.answer(query)
            
            # Display answer
            print(f"\n🤖 Assistant: {result['answer']}")
            print_separator()
            
            # Display routing info (optional, but useful for understanding agentic behavior)
            routing = result['routing']
            route_type = "RAG (Policy)" if result['used_rag'] else "Direct LLM"
            print(f"📊 Route: {route_type} | Needs Policy: {routing['needs_policy']}")
            if routing['reasoning']:
                print(f"   Reasoning: {routing['reasoning']}")
            
            # Display evaluation
            if result.get('evaluation'):
                eval_info = result['evaluation']
                if 'error' in eval_info:
                    print(f"   Evaluation Error: {eval_info['error']}")
                else:
                    print(f"   Evaluation: {eval_info['verdict']} | "
                          f"Relevance={eval_info['relevance_score']:.2f} | "
                          f"Faithfulness={eval_info['faithfulness_score']:.2f} | "
                          f"Overall={eval_info['overall_score']:.2f}")
                    if eval_info['suggestions'] and eval_info['suggestions'] != 'None':
                        print(f"   Suggestions: {eval_info['suggestions']}")
            print_separator()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print_separator()


if __name__ == "__main__":
    main()


