from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Optional
import google.generativeai as genai
from vector_store import VectorStore
from tavily import TavilyClient
import re

# Enhanced State definition with query classification
class RAGState(TypedDict):
    # Original fields
    user_query: str
    retrieved_documents: List[Dict]
    augmented_prompt: str
    final_response: str
    error: str
    
    # Document retrieval fields
    local_documents: List[Dict]
    web_documents: List[Dict] 
    llm_says_sufficient: bool
    web_search_performed: bool
    
    # Chat history field
    chat_history_context: str
    
    # New fields for enhanced pipeline
    query_type: str  # 'casual', 'question_from_history', 'question_needs_retrieval'
    temperature: float  # Dynamic temperature based on query type
    answer_from_history: Optional[str]  # If answer found in history
    skip_retrieval: bool  # Flag to skip retrieval 
    
    session_id: Optional[str] 

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
        """Create enhanced LangGraph workflow with query classification"""
        workflow = StateGraph(RAGState)
        
        # Add nodes
        workflow.add_node("classify_query", self._classify_query)
        workflow.add_node("check_history_for_answer", self._check_history_for_answer)
        workflow.add_node("local_retrieve", self._local_retrieve_documents)
        workflow.add_node("llm_check_sufficiency", self._llm_check_sufficiency)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("combine_sources", self._combine_sources)
        workflow.add_node("augment", self._augment_prompt)
        workflow.add_node("generate", self._generate_response)
        workflow.add_node("generate_casual", self._generate_casual_response)
        workflow.add_node("generate_from_history", self._generate_from_history)
        
        # Entry point
        workflow.set_entry_point("classify_query")
        
        # Routing from query classification
        workflow.add_conditional_edges(
            "classify_query",
            self._route_after_classification,
            {
                "casual": "generate_casual",
                "check_history": "check_history_for_answer",
                "retrieval": "local_retrieve"
            }
        )
        
        # Routing from history check
        workflow.add_conditional_edges(
            "check_history_for_answer",
            self._route_after_history_check,
            {
                "found": "generate_from_history",
                "not_found": "local_retrieve"
            }
        )
        
        # Rest of the flow
        workflow.add_edge("local_retrieve", "llm_check_sufficiency")
        
        workflow.add_conditional_edges(
            "llm_check_sufficiency",
            self._decide_next_action,
            {
                "web_search": "web_search",
                "combine_sources": "combine_sources"
            }
        )
        
        workflow.add_edge("web_search", "combine_sources")
        workflow.add_edge("combine_sources", "augment")
        workflow.add_edge("augment", "generate")
        
        # All generation nodes lead to END
        workflow.add_edge("generate", END)
        workflow.add_edge("generate_casual", END)
        workflow.add_edge("generate_from_history", END)
        
        return workflow.compile()
    
    def _classify_query(self, state: RAGState) -> RAGState:
        """Classify the query type and determine appropriate handling"""
        try:
            user_query = state["user_query"]
            chat_history = state.get("chat_history_context", "")
            
            # Classification prompt
            classification_prompt = f"""Analyze the following user input and classify it into one of three categories:

1. "casual" - Casual conversation, greetings, statements about themselves, social interactions, or anything that doesn't require information retrieval
2. "history_question" - A question that can be answered from the conversation history
3. "retrieval_question" - A question that requires searching documents or web for information

Conversation History:
{chat_history if chat_history else "No previous conversation"}

Current User Input: "{user_query}"

Classification Guidelines:
- If the user is making a statement about themselves (name, preferences, etc.), it's "casual"
- If the user is greeting or having social conversation, it's "casual"
- If the user is asking about something mentioned in the conversation history, it's "history_question"
- If the user is asking for information not in the history, it's "retrieval_question"

Respond with ONLY one of these three words: casual, history_question, or retrieval_question"""

            response = self.gemini_model.generate_content(classification_prompt)
            classification = response.text.strip().lower()
            
            # Parse classification
            if "casual" in classification:
                state["query_type"] = "casual"
                state["temperature"] = 0.7  # Higher temperature for casual conversation
                state["skip_retrieval"] = True
            elif "history_question" in classification:
                state["query_type"] = "question_from_history"
                state["temperature"] = 0.3  # Lower temperature for factual recall
                state["skip_retrieval"] = False  # May need retrieval if history doesn't have answer
            else:
                state["query_type"] = "question_needs_retrieval"
                state["temperature"] = 0.2  # Low temperature for factual retrieval
                state["skip_retrieval"] = False
            
            print(f"DEBUG: Query classified as: {state['query_type']}, Temperature: {state['temperature']}")
            return state
            
        except Exception as e:
            # Default to retrieval on error
            state["query_type"] = "question_needs_retrieval"
            state["temperature"] = 0.2
            state["skip_retrieval"] = False
            state["error"] = f"Classification error: {str(e)}"
            return state
    
    def _route_after_classification(self, state: RAGState) -> str:
        """Route based on query classification"""
        query_type = state.get("query_type", "question_needs_retrieval")
        
        if query_type == "casual":
            return "casual"
        elif query_type == "question_from_history":
            return "check_history"
        else:
            return "retrieval"
    
    def _check_history_for_answer(self, state: RAGState) -> RAGState:
        """Check if the answer exists in conversation history"""
        try:
            user_query = state["user_query"]
            chat_history = state.get("chat_history_context", "")
            
            if not chat_history:
                state["answer_from_history"] = None
                return state
            
            # Ask LLM if history contains the answer
            history_check_prompt = f"""Based on the conversation history below, can you answer the user's question?

Conversation History:
{chat_history}

User's Question: "{user_query}"

If the conversation history contains information to answer this question, respond with "YES: [the answer]"
If the conversation history does NOT contain enough information, respond with "NO"

Your response:"""

            response = self.gemini_model.generate_content(history_check_prompt)
            llm_response = response.text.strip()
            
            if llm_response.startswith("YES:"):
                # Extract the answer
                answer = llm_response[4:].strip()
                state["answer_from_history"] = answer
                state["skip_retrieval"] = True
                print(f"DEBUG: Found answer in history: {answer[:50]}...")
            else:
                state["answer_from_history"] = None
                state["skip_retrieval"] = False
                print("DEBUG: Answer not found in history, proceeding to retrieval")
            
            return state
            
        except Exception as e:
            state["answer_from_history"] = None
            state["skip_retrieval"] = False
            state["error"] = f"History check error: {str(e)}"
            return state
    
    def _route_after_history_check(self, state: RAGState) -> str:
        """Route based on whether answer was found in history"""
        if state.get("answer_from_history"):
            return "found"
        else:
            return "not_found"
    
    def _generate_casual_response(self, state: RAGState) -> RAGState:
        """Generate response for casual conversation"""
        try:
            user_query = state["user_query"]
            chat_history = state.get("chat_history_context", "")
            temperature = state.get("temperature", 0.7)
            
            # Casual conversation prompt
            casual_prompt = f"""You are a friendly and helpful AI assistant engaged in casual conversation.

Previous Conversation:
{chat_history if chat_history else "This is the start of our conversation."}

User: {user_query}

Instructions:
- Respond naturally and conversationally
- Remember and reference previous parts of the conversation when relevant
- Be warm, friendly, and engaging
- If the user shares information about themselves, acknowledge it appropriately
- Keep the conversation flowing naturally

Your response:"""

            # Configure model with dynamic temperature
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=500,
            )
            
            response = self.gemini_model.generate_content(
                casual_prompt,
                generation_config=generation_config
            )
            
            state["final_response"] = response.text
            print(f"DEBUG: Generated casual response with temperature {temperature}")
            return state
            
        except Exception as e:
            state["error"] = f"Casual generation error: {str(e)}"
            state["final_response"] = "I'm sorry, I had trouble processing that. Could you please rephrase?"
            return state
    
    def _generate_from_history(self, state: RAGState) -> RAGState:
        """Generate response using answer from history"""
        try:
            answer_from_history = state.get("answer_from_history", "")
            user_query = state["user_query"]
            chat_history = state.get("chat_history_context", "")
            temperature = state.get("temperature", 0.3)
            
            # Refine the answer from history
            refine_prompt = f"""Based on our conversation history, provide a natural response to the user's question.

Conversation History:
{chat_history}

User's Question: {user_query}

Information from our conversation: {answer_from_history}

Provide a natural, conversational response that directly answers their question:"""

            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=500,
            )
            
            response = self.gemini_model.generate_content(
                refine_prompt,
                generation_config=generation_config
            )
            
            state["final_response"] = response.text
            print(f"DEBUG: Generated response from history with temperature {temperature}")
            return state
            
        except Exception as e:
            state["error"] = f"History generation error: {str(e)}"
            state["final_response"] = state.get("answer_from_history", "I had trouble formulating the response.")
            return state
    
    def _local_retrieve_documents(self, state: RAGState) -> RAGState:
        """Retrieve relevant documents from local vector store"""
        try:
            # Skip if marked for skipping
            if state.get("skip_retrieval", False):
                state["local_documents"] = []
                return state
            
            user_query = state["user_query"]
            session_id = state.get("session_id")  # 🔑 Get session_id from state
            
            # ✅ Pass session_id to ensure session-scoped retrieval
            retrieved_docs = self.vector_store.similarity_search(
                query=user_query, 
                k=5, 
                session_id=session_id
            )
            
            state["local_documents"] = retrieved_docs
            print(f"DEBUG: Retrieved {len(retrieved_docs)} local documents for session {session_id}")
            return state
        except Exception as e:
            state["error"] = f"Local retrieval error: {str(e)}"
            state["local_documents"] = []
            return state
    
    def _llm_check_sufficiency(self, state: RAGState) -> RAGState:
        """LLM evaluation: Can local docs answer the query?"""
        try:
            user_query = state["user_query"]
            local_docs = state["local_documents"]
            chat_history = state.get("chat_history_context", "")
            
            if not local_docs:
                state["llm_says_sufficient"] = False
                return state
            
            # Format documents for LLM
            docs_text = ""
            for i, doc in enumerate(local_docs, 1):
                title = doc.get("title", f"Document {i}")
                content = doc.get("content", "")
                docs_text += f"Document {i} - {title}:\n{content}\n\n"
            
            # Include chat history in evaluation if available
            context_prefix = ""
            if chat_history:
                context_prefix = f"Considering the conversation history:\n{chat_history}\n\n"
            
            # Evaluation prompt
            evaluation_prompt = f"""{context_prefix}Query: {user_query}

Available Documents:
{docs_text}

Can these documents fully answer the user's query? 
Respond with only "Yes" or "No" - nothing else."""
            
            response = self.gemini_model.generate_content(evaluation_prompt)
            llm_response = response.text.strip().lower()
            
            if "yes" in llm_response:
                state["llm_says_sufficient"] = True
            else:
                state["llm_says_sufficient"] = False
            
            print(f"DEBUG: Local docs sufficient: {state['llm_says_sufficient']}")
            return state
        except Exception as e:
            state["llm_says_sufficient"] = False
            state["error"] = f"LLM evaluation error: {str(e)}"
            return state
    
    def _decide_next_action(self, state: RAGState) -> str:
        """Decision: sufficient or need web search?"""
        if not self.tavily_client:
            return "combine_sources"
        
        if state["llm_says_sufficient"]:
            return "combine_sources"
        else:
            return "web_search"
    
    def _web_search(self, state: RAGState) -> RAGState:
        """Search web using Tavily"""
        try:
            if not self.tavily_client:
                state["error"] = "Tavily client not configured"
                state["web_documents"] = []
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
            print(f"DEBUG: Retrieved {len(web_docs)} web documents")
            return state
        except Exception as e:
            state["error"] = f"Web search error: {str(e)}"
            state["web_documents"] = []
            return state
    
    def _combine_sources(self, state: RAGState) -> RAGState:
        """Combine local and web documents"""
        try:
            all_documents = []
            
            # Add local documents first (prioritized)
            for doc in state.get("local_documents", []):
                doc_copy = doc.copy()
                doc_copy["source_type"] = "local"
                all_documents.append(doc_copy)
            
            # Add web documents
            for doc in state.get("web_documents", []):
                all_documents.append(doc)
            
            state["retrieved_documents"] = all_documents
            print(f"DEBUG: Combined {len(all_documents)} total documents")
            return state
        except Exception as e:
            state["error"] = f"Source combination error: {str(e)}"
            state["retrieved_documents"] = []
            return state
    
    def _augment_prompt(self, state: RAGState) -> RAGState:
        """Create augmented prompt with context and chat history"""
        try:
            user_query = state["user_query"]
            retrieved_docs = state["retrieved_documents"]
            chat_history = state.get("chat_history_context", "")
            
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
            
            # Include chat history if available
            history_section = ""
            if chat_history:
                history_section = f"""## CONVERSATION HISTORY:
{chat_history}

"""
            
            # Create augmented prompt
            augmented_prompt = f"""{history_section}You are a helpful AI assistant. Use the information from the retrieved context and conversation history to answer the question.

Instructions:
- Provide a comprehensive answer based on the retrieved information
- Be conversational and natural in your response
- Reference previous conversation when relevant
- If the context doesn't contain relevant information, acknowledge this and provide the best answer you can
- Cite source documents when appropriate

## RETRIEVED CONTEXT:
{context if context else "No relevant documents found."}

## USER QUESTION:
{user_query}

Your response:"""
            
            state["augmented_prompt"] = augmented_prompt
            return state
        except Exception as e:
            state["error"] = f"Augmentation error: {str(e)}"
            return state
    
    def _generate_response(self, state: RAGState) -> RAGState:
        """Generate response using Gemini with dynamic temperature"""
        try:
            augmented_prompt = state["augmented_prompt"]
            temperature = state.get("temperature", 0.2)
            
            # Configure generation with dynamic temperature
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=1000,
            )
            
            response = self.gemini_model.generate_content(
                augmented_prompt,
                generation_config=generation_config
            )
            
            state["final_response"] = response.text
            print(f"DEBUG: Generated retrieval response with temperature {temperature}")
            return state
        except Exception as e:
            state["error"] = f"Generation error: {str(e)}"
            state["final_response"] = "I encountered an error while generating the response."
            return state
    
    def run(self, user_query: str, chat_history_context: str = "", session_id: Optional[str] = None) -> Dict:
        """Run the complete enhanced RAG pipeline"""
        initial_state = {
            # Original fields
            "user_query": user_query,
            "retrieved_documents": [],
            "augmented_prompt": "",
            "final_response": "",
            "error": "",
            
            # Document retrieval fields
            "local_documents": [],
            "web_documents": [],
            "llm_says_sufficient": False,
            "web_search_performed": False,
            
            # Chat history
            "chat_history_context": chat_history_context,
            
            # New fields
            "query_type": "",
            "temperature": 0.2,
            "answer_from_history": None,
            "skip_retrieval": False,
            "session_id": session_id
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            if final_state.get("error"):
                # Don't expose internal errors for casual conversation
                if final_state.get("query_type") == "casual":
                    return {
                        "response": "I'm sorry, I had trouble understanding that. Could you please rephrase?",
                        "status": "success",
                        "query_type": final_state.get("query_type", "unknown"),
                        "temperature": final_state.get("temperature", 0.2),
                        "retrieved_docs_count": 0,
                        "web_search_used": False
                    }
                else:
                    return {
                        "response": f"Sorry, I encountered an error: {final_state['error']}",
                        "status": "error",
                        "query_type": final_state.get("query_type", "unknown"),
                        "temperature": final_state.get("temperature", 0.2),
                        "retrieved_docs_count": 0,
                        "web_search_used": False
                    }
            
            return {
                "response": final_state["final_response"],
                "status": "success",
                "query_type": final_state.get("query_type", "unknown"),
                "temperature": final_state.get("temperature", 0.2),
                "retrieved_docs_count": len(final_state.get("retrieved_documents", [])),
                "llm_evaluation": final_state.get("llm_says_sufficient"),
                "web_search_used": final_state.get("web_search_performed", False),
                "answered_from_history": final_state.get("answer_from_history") is not None
            }
        except Exception as e:
            return {
                "response": f"Pipeline error: {str(e)}",
                "status": "error",
                "query_type": "unknown",
                "temperature": 0.2,
                "retrieved_docs_count": 0,
                "web_search_used": False
            }
    
    def close(self):
        """Clean up resources"""
        self.vector_store.close()