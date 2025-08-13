from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
import google.generativeai as genai
from vector_store import VectorStore
from tavily import TavilyClient

# Simple State definition for the RAG pipeline with LLM evaluation
class RAGState(TypedDict):
    # Original fields
    user_query: str
    retrieved_documents: List[Dict]
    augmented_prompt: str
    final_response: str
    error: str
    
    # Simple new fields
    local_documents: List[Dict]
    web_documents: List[Dict] 
    llm_says_sufficient: bool
    web_search_performed: bool

class RAGPipeline:
    def __init__(self, gemini_model, tavily_api_key: str = None):
        self.vector_store = VectorStore()
        self.gemini_model = gemini_model
        
        # Initialize Tavily client if API key provided
        self.tavily_client = None
        if tavily_api_key:
            try:
                self.tavily_client = TavilyClient(api_key=tavily_api_key)
                print(f"DEBUG: Tavily client initialized successfully")
            except Exception as e:
                print(f"DEBUG: Failed to initialize Tavily client: {e}")
                self.tavily_client = None
        else:
            print("DEBUG: No Tavily API key provided")
        
        self.graph = self._create_graph()
    
    def _create_graph(self):
        """Create simple LangGraph workflow with LLM-based decision making"""
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("local_retrieve", self._local_retrieve_documents)
        workflow.add_node("llm_check_sufficiency", self._llm_check_sufficiency)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("combine_sources", self._combine_sources)
        workflow.add_node("augment", self._augment_prompt)
        workflow.add_node("generate", self._generate_response)
        
        # Simple flow
        workflow.set_entry_point("local_retrieve")
        workflow.add_edge("local_retrieve", "llm_check_sufficiency")
        
        # SIMPLE CONDITIONAL ROUTING
        workflow.add_conditional_edges(
            "llm_check_sufficiency",
            self._decide_next_action,
            {
                "web_search": "web_search",
                "combine_sources": "combine_sources"
            }
        )
        
        # Converge paths
        workflow.add_edge("web_search", "combine_sources")
        workflow.add_edge("combine_sources", "augment")
        workflow.add_edge("augment", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def _local_retrieve_documents(self, state: RAGState) -> RAGState:
        """Retrieve relevant documents from local vector store"""
        try:
            user_query = state["user_query"]
            retrieved_docs = self.vector_store.similarity_search(user_query, k=5)
            
            state["local_documents"] = retrieved_docs
            return state
        except Exception as e:
            state["error"] = f"Local retrieval error: {str(e)}"
            return state
    
    def _llm_check_sufficiency(self, state: RAGState) -> RAGState:
        """Simple LLM evaluation: Can local docs answer the query?"""
        try:
            user_query = state["user_query"]
            local_docs = state["local_documents"]
            
            if not local_docs:
                state["llm_says_sufficient"] = False
                return state
            
            # Format documents for LLM
            docs_text = ""
            for i, doc in enumerate(local_docs, 1):
                title = doc.get("title", f"Document {i}")
                content = doc.get("content", "")
                docs_text += f"Document {i} - {title}:\n{content}\n\n"
            
            # Simple evaluation prompt
            evaluation_prompt = f"""Query: {user_query}

Available Documents:
{docs_text}

Can these documents fully answer the user's query? 
Respond with only "Yes" or "No" - nothing else."""
            
            # Get LLM response
            response = self.gemini_model.generate_content(evaluation_prompt)
            llm_response = response.text.strip().lower()
            
            # Parse yes/no response
            if "yes" in llm_response:
                state["llm_says_sufficient"] = True
            else:
                state["llm_says_sufficient"] = False
            
            return state
        except Exception as e:
            # If LLM evaluation fails, assume insufficient (safer to over-search)
            state["llm_says_sufficient"] = False
            state["error"] = f"LLM evaluation error: {str(e)}"
            return state
    
    def _decide_next_action(self, state: RAGState) -> str:
        """Simple decision: sufficient or need web search?"""
        if not self.tavily_client:
            return "combine_sources"  # No web search available
        
        if state["llm_says_sufficient"]:
            return "combine_sources"  # LLM says local docs are sufficient
        else:
            return "web_search"       # LLM says need more info
    
    def _web_search(self, state: RAGState) -> RAGState:
        """Search web using Tavily"""
        try:
            if not self.tavily_client:
                state["error"] = "Tavily client not configured"
                return state
            
            search_results = self.tavily_client.search(
                query=state["user_query"],
                max_results=3,
                include_answer=True,
                include_raw_content=False
            )
            
            # Convert to document format
            web_docs = []
            for i, result in enumerate(search_results.get('results', []), 1):
                web_doc = {
                    "content": result['content'],
                    "title": result.get('title', f'Web Document {i}'),
                    "url": result['url'],
                    "score": 0.9,
                    "source_type": "web"
                }
                web_docs.append(web_doc)
            
            state["web_documents"] = web_docs
            state["web_search_performed"] = True
            return state
        except Exception as e:
            state["error"] = f"Web search error: {str(e)}"
            return state
    
    def _combine_sources(self, state: RAGState) -> RAGState:
        """Combine local and web documents"""
        try:
            all_documents = []
            
            # Add local documents first (prioritized)
            for doc in state["local_documents"]:
                doc_copy = doc.copy()
                doc_copy["source_type"] = "local"
                all_documents.append(doc_copy)
            
            # Add web documents
            for doc in state["web_documents"]:
                all_documents.append(doc)
            
            state["retrieved_documents"] = all_documents
            return state
        except Exception as e:
            state["error"] = f"Source combination error: {str(e)}"
            return state
    
    def _augment_prompt(self, state: RAGState) -> RAGState:
        """Create augmented prompt with context (original implementation enhanced)"""
        try:
            user_query = state["user_query"]
            retrieved_docs = state["retrieved_documents"]
            
            # Format documents with source attribution
            context = ""
            for i, doc in enumerate(retrieved_docs, 1):
                content = doc.get("content", "")
                title = doc.get("title", f"Document {i}")
                score = doc.get("score", 0)
                source_type = doc.get("source_type", "local")
                
                if source_type == "local":
                    context += f"\n--- Local Document {i}: {title} (Relevance: {score:.3f}) ---\n{content}\n"
                else:
                    url = doc.get("url", "")
                    context += f"\n--- Web Document {i}: {title}\nURL: {url} ---\n{content}\n"
            
            # Create augmented prompt
            augmented_prompt = f"""Using the information contained in the context,
give a comprehensive answer to the question.
Respond only to the question asked, response should be concise and relevant to the question.
Provide the number of the source document when relevant.
If the answer cannot be deduced from the context, answer with "no relevant context"

## RETRIEVED CONTEXT:
{context}

## USER QUESTION:
{user_query}

"""
            
            state["augmented_prompt"] = augmented_prompt
            return state
        except Exception as e:
            state["error"] = f"Augmentation error: {str(e)}"
            return state
    
    def _generate_response(self, state: RAGState) -> RAGState:
        """Generate response using Gemini (original implementation)"""
        try:
            augmented_prompt = state["augmented_prompt"]
            response = self.gemini_model.generate_content(augmented_prompt)
            
            state["final_response"] = response.text 
            return state
        except Exception as e:
            state["error"] = f"Generation error: {str(e)}"
            return state
    
    def run(self, user_query: str) -> Dict:
        """Run the complete RAG pipeline (same interface as before)"""
        initial_state = {
            # Original fields
            "user_query": user_query,
            "retrieved_documents": [],
            "augmented_prompt": "",
            "final_response": "",
            "error": "",
            
            # Simple new fields
            "local_documents": [],
            "web_documents": [],
            "llm_says_sufficient": False,
            "web_search_performed": False
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            if final_state.get("error"):
                return {
                    "response": f"Sorry, I encountered an error: {final_state['error']}",
                    "status": "error",
                    "retrieved_docs_count": 0,
                    "llm_evaluation": final_state.get("llm_says_sufficient"),
                    "web_search_used": final_state.get("web_search_performed", False)
                }
            
            return {
                "response": final_state["final_response"],
                "status": "success",
                "retrieved_docs_count": len(final_state["retrieved_documents"]),
                "llm_evaluation": final_state["llm_says_sufficient"],
                "web_search_used": final_state["web_search_performed"]
            }
        except Exception as e:
            return {
                "response": f"Pipeline error: {str(e)}",
                "status": "error",
                "retrieved_docs_count": 0,
                "llm_evaluation": False,
                "web_search_used": False
            }
    
    def close(self):
        """Clean up resources"""
        self.vector_store.close()