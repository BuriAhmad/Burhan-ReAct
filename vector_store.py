from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional
from config import config

class VectorStore:
    def __init__(self):
        self.client = MongoClient(config.MONGODB_URI)
        self.db = self.client[config.DATABASE_NAME]
        self.collection = self.db[config.COLLECTION_NAME]
        self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
        
        # Updated index name for the optimized Atlas index
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()
    
    def vector_search(self, query_embedding: List[float], k: int = None, session_id: Optional[str] = None) -> List[Dict]:
        if k is None:
            k = config.SIMILARITY_SEARCH_LIMIT

        # ✅ OPTIMIZED: Using the new Atlas index with built-in filtering
        vector_stage = {
            "$vectorSearch": {
                "index": config.VECTOR_INDEX_NAME,  # 🎯 New optimized index
                "path": config.EMBEDDING_FIELD_NAME,
                "queryVector": query_embedding,
                "numCandidates": k * 2,
                "limit": k
            }
        }

        # ✅ IMPROVED: Session filtering now uses the optimized index
        if session_id:
            vector_stage["$vectorSearch"]["filter"] = {
                "metadata.session_id": {"$eq": session_id}
            }

        pipeline = [
            vector_stage,
            {
                "$project": {
                    "content": 1,
                    "metadata": 1,
                    "score": {"$meta": "vectorSearchScore"},
                    "_id": 0
                }
            }
        ]
        
        return list(self.collection.aggregate(pipeline))
    
    def similarity_search(self, query: str, k: int = None, session_id: Optional[str] = None) -> List[Dict]:
        """
        Perform similarity search with session isolation
        Now much faster due to optimized Atlas index!
        """
        if k is None:
            k = config.SIMILARITY_SEARCH_LIMIT
        query_embedding = self.generate_embedding(query)
        return self.vector_search(query_embedding, k, session_id=session_id)
    
    def store_pdf_chunks(self, chunks: List[Dict], session_id: str) -> Dict:
        """Store PDF chunks with session metadata (unchanged)"""
        try:
            documents_to_insert = []
            for chunk in chunks:
                embedding = self.generate_embedding(chunk['content'])
                document = {
                    'content': chunk['content'],
                    config.EMBEDDING_FIELD_NAME: embedding,
                    'metadata': {
                        'session_id': session_id,
                        'source_file': chunk.get('source_file'),
                        'page_number': chunk.get('page_number'),
                        'chunk_index': chunk.get('chunk_index'),
                        'upload_timestamp': chunk.get('upload_timestamp'),
                        'document_type': chunk.get('document_type'),
                        'word_count': chunk.get('word_count')
                    }
                }
                documents_to_insert.append(document)
            
            result = self.collection.insert_many(documents_to_insert)
            return {
                'success': True,
                'inserted_count': len(result.inserted_ids),
                'inserted_ids': [str(id) for id in result.inserted_ids]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_session_documents(self, session_id: str) -> Dict:
        """Delete all documents for a session (unchanged but now more efficient)"""
        try:
            res = self.collection.delete_many({"metadata.session_id": session_id})
            return {"success": True, "deleted_count": res.deleted_count}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_session_document_stats(self, session_id: str) -> Dict:
        """Get statistics about documents in a session"""
        try:
            # Count documents
            doc_count = self.collection.count_documents({"metadata.session_id": session_id})
            
            # Get file breakdown
            pipeline = [
                {"$match": {"metadata.session_id": session_id}},
                {"$group": {
                    "_id": "$metadata.source_file",
                    "chunk_count": {"$sum": 1},
                    "total_words": {"$sum": "$metadata.word_count"}
                }}
            ]
            
            file_stats = list(self.collection.aggregate(pipeline))
            
            return {
                "success": True,
                "total_documents": doc_count,
                "files": file_stats
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()