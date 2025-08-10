from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
import google.generativeai as genai
from vector_store import VectorStore

# State definition for the RAG pipeline
class RAGState(TypedDict):
    user_query: str
    retrieved_documents: List[Dict]
    augmented_prompt: str
    final_response: str
    error: str

class RAGPipeline:
    def __init__(self, gemini_model):
        self.vector_store = VectorStore()
        self.gemini_model = gemini_model
        self.graph = self._create_graph()
    
    def _create_graph(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("retrieve", self._retrieve_documents)
        workflow.add_node("augment", self._augment_prompt)
        workflow.add_node("generate", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "augment")
        workflow.add_edge("augment", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    def _retrieve_documents(self, state: RAGState) -> RAGState:
        """Retrieve relevant documents from vector store"""
        try:
            user_query = state["user_query"]
            retrieved_docs = self.vector_store.similarity_search(user_query, k=5)
            
            state["retrieved_documents"] = retrieved_docs
            return state
        except Exception as e:
            state["error"] = f"Retrieval error: {str(e)}"
            return state
    
    def _augment_prompt(self, state: RAGState) -> RAGState:
        """Create augmented prompt with context"""
        try:
            user_query = state["user_query"]
            retrieved_docs = state["retrieved_documents"]
            
            # Format retrieved documents as context
            context = ""
            for i, doc in enumerate(retrieved_docs, 1):
                content = doc.get("content", "")
                title = doc.get("title", f"Document {i}")
                score = doc.get("score", 0)
                context += f"\n--- Document {i}: {title} (Relevance: {score:.3f}) ---\n{content}\n"
            
            # Create augmented prompt
            augmented_prompt = f"""Using the information contained in the context,
give a comprehensive answer to the question.
Respond only to the question asked, response should be concise and relevant to the question.
Provide the number of the source document used.
If the answer cannot be deduced from the context, answer with "no information foud".

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
        """Generate response using Gemini with augmented prompt"""
        try:
            augmented_prompt = state["augmented_prompt"]
            response = self.gemini_model.generate_content(augmented_prompt)
            
            state["final_response"] = response.text
            return state
        except Exception as e:
            state["error"] = f"Generation error: {str(e)}"
            return state
    
    def run(self, user_query: str) -> Dict:
        """Run the complete RAG pipeline"""
        initial_state = {
            "user_query": user_query,
            "retrieved_documents": [],
            "augmented_prompt": "",
            "final_response": "",
            "error": ""
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            if final_state.get("error"):
                return {
                    "response": f"Sorry, I encountered an error: {final_state['error']}",
                    "status": "error",
                    "retrieved_docs_count": 0
                }
            
            return {
                "response": final_state["final_response"],
                "status": "success",
                "retrieved_docs_count": len(final_state["retrieved_documents"])
            }
        except Exception as e:
            return {
                "response": f"Pipeline error: {str(e)}",
                "status": "error",
                "retrieved_docs_count": 0
            }
    
    def close(self):
        """Clean up resources"""
        self.vector_store.close()