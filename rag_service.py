from typing import List, Dict, Any
import json
from mongodb_service import MongoDBService
from config import config

class RAGService:
    def __init__(self, mongodb_service: MongoDBService):
        self.mongodb_service = mongodb_service
        
        # Default RAG prompt template
        self.system_prompt = """You are a helpful AI assistant with access to a knowledge base. 
Use the provided context documents to answer the user's question accurately and comprehensively. 
If the context doesn't contain relevant information, clearly state that and provide the best answer you can based on your general knowledge.

CONTEXT DOCUMENTS:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
- Answer based primarily on the provided context
- If context is insufficient, clearly indicate this
- Be specific and cite relevant information from the context
- Maintain accuracy and avoid hallucinating information not present in the context
"""
    
    def set_prompt_template(self, template: str):
        """Set custom prompt template"""
        self.system_prompt = template
    
    def format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context string"""
        if not documents:
            return "No relevant documents found in the knowledge base."
        
        formatted_docs = []
        for i, doc in enumerate(documents, 1):
            # Remove MongoDB _id for cleaner output
            doc_copy = {k: v for k, v in doc.items() if k != '_id'}
            
            # Try to extract main content fields
            content = ""
            for field in ['content', 'text', 'description', 'title']:
                if field in doc_copy:
                    content += f"{field.capitalize()}: {doc_copy[field]}\n"
            
            # If no standard fields found, use the whole document
            if not content:
                content = json.dumps(doc_copy, indent=2)
            
            formatted_docs.append(f"Document {i}:\n{content}")
        
        return "\n" + "="*50 + "\n".join(formatted_docs) + "\n" + "="*50
    
    def retrieve_and_augment(self, 
                           question: str,
                           collection_name: str = None,
                           database_name: str = None,
                           limit: int = None,
                           search_fields: List[str] = None) -> str:
        """
        Retrieve relevant documents and create augmented prompt
        """
        # Use config defaults if not provided
        database_name = database_name or config.DATABASE_NAME
        collection_name = collection_name or config.COLLECTION_NAME
        limit = limit or config.SIMILARITY_SEARCH_LIMIT
        
        # Set database
        self.mongodb_service.set_database(database_name)
        
        # Retrieve relevant documents
        documents = self.mongodb_service.search_documents(
            collection_name=collection_name,
            query=question,
            limit=limit,
            search_fields=search_fields
        )
        
        # Format documents as context
        context = self.format_documents(documents)
        
        # Create augmented prompt
        augmented_prompt = self.system_prompt.format(
            context=context,
            question=question
        )
        
        return augmented_prompt
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about available databases and collections"""
        info = {}
        try:
            # You might want to set a default database first
            databases = self.mongodb_service.client.list_database_names()
            info["databases"] = databases
            info["current_database"] = config.DATABASE_NAME
            info["current_collection"] = config.COLLECTION_NAME
            
            # For each database, get collections (limiting to avoid too much data)
            for db_name in databases[:5]:  # Limit to first 5 databases
                self.mongodb_service.set_database(db_name)
                collections = self.mongodb_service.get_collections()
                info[f"{db_name}_collections"] = collections
                
        except Exception as e:
            info["error"] = str(e)
        
        return info