from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict

# Configuration
MONGODB_URI = "mongodb+srv://buri:buri_password@cluster0.gtzff0e.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "your_database_name"  
COLLECTION_NAME = "your_collection_name"  
EMBEDDING_FIELD_NAME = "embedding"
EMBEDDING_MODEL_NAME = "thenlper/gte-small"

class VectorStore:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.collection = self.db[COLLECTION_NAME]
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()
    
    def vector_search(self, query_embedding: List[float], k: int = 5) -> List[Dict]:
        """Perform vector search in MongoDB"""
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Make sure this matches your index name
                    "path": EMBEDDING_FIELD_NAME,
                    "queryVector": query_embedding,
                    "numCandidates": k * 2,
                    "limit": k
                }
            },
            {
                "$project": {
                    "content": 1,  # Adjust field names based on your document structure
                    "score": {"$meta": "vectorSearchScore"},
                    "_id": 0
                }
            }
        ]
        #print(pipeline)
        results = list(self.collection.aggregate(pipeline))
        return results
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """Generate embedding for query and perform similarity search"""
        query_embedding = self.generate_embedding(query)
        return self.vector_search(query_embedding, k)
    
    def store_pdf_chunks(self, chunks: List[Dict]) -> Dict:
        """Store PDF chunks with embeddings in MongoDB"""
        try:
            documents_to_insert = []
            
            for chunk in chunks:
                # Generate embedding for chunk content
                embedding = self.generate_embedding(chunk['content'])
                
                # Create document for MongoDB
                document = {
                    'content': chunk['content'],
                    'embedding': embedding,
                    'metadata': {
                        'source_file': chunk.get('source_file'),
                        'page_number': chunk.get('page_number'),
                        'chunk_index': chunk.get('chunk_index'),
                        'upload_timestamp': chunk.get('upload_timestamp'),
                        'document_type': chunk.get('document_type'),
                        'word_count': chunk.get('word_count')
                    }
                }
                documents_to_insert.append(document)
            
            # Batch insert all documents
            result = self.collection.insert_many(documents_to_insert)
            
            return {
                'success': True,
                'inserted_count': len(result.inserted_ids),
                'inserted_ids': [str(id) for id in result.inserted_ids]
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()