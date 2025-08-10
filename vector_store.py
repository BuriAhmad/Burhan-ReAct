from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict

# Configuration
MONGODB_URI = "mongodb+srv://buri:buri_password@cluster0.gtzff0e.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "your_database_name"  # Replace with your actual database name
COLLECTION_NAME = "your_collection_name"  # Replace with your actual collection name
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
                    "title": 1,    # Adjust field names based on your document structure
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        results = list(self.collection.aggregate(pipeline))
        return results
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """Generate embedding for query and perform similarity search"""
        query_embedding = self.generate_embedding(query)
        return self.vector_search(query_embedding, k)
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()