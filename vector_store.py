import os
import json
import numpy as np
from openai import OpenAI

class SimpleVectorStore:
    def __init__(self, db_path: str = "vector_db.json"):
        self.db_path = db_path
        self.chunks = []
        self.embeddings = []
        self.load()

    def get_client(self, api_key: str):
        """Returns an OpenAI client pointing to the NVIDIA API Catalog."""
        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )

    def add_documents(self, chunks: list, api_key: str):
        """Generates embeddings for chunks and adds them to the store."""
        if not chunks:
            return
        
        client = self.get_client(api_key)
        texts = [c["text"] for c in chunks]
        
        # Batch embedding requests (limit 32 chunks per call to stay safe)
        batch_size = 16
        new_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            response = client.embeddings.create(
                model="nvidia/nv-embedqa-e5-v5",
                input=batch_texts,
                extra_body={"input_type": "passage"}
            )
            for data in response.data:
                new_embeddings.append(data.embedding)
                
        # Append to our local store
        for chunk, embedding in zip(chunks, new_embeddings):
            self.chunks.append({
                "text": chunk["text"],
                "metadata": chunk["metadata"]
            })
            self.embeddings.append(embedding)
            
        self.save()

    def similarity_search(self, query: str, api_key: str, k: int = 5):
        """Searches the vector store using cosine similarity."""
        if not self.chunks:
            return []
            
        client = self.get_client(api_key)
        
        # Get query embedding
        response = client.embeddings.create(
            model="nvidia/nv-embedqa-e5-v5",
            input=[query],
            extra_body={"input_type": "query"}
        )
        query_vector = np.array(response.data[0].embedding)
        
        # Calculate cosine similarities
        db_vectors = np.array(self.embeddings)
        
        # Cosine similarity = (A . B) / (||A|| * ||B||)
        dot_products = np.dot(db_vectors, query_vector)
        db_norms = np.linalg.norm(db_vectors, axis=1)
        query_norm = np.linalg.norm(query_vector)
        
        # Handle zero norms safely
        db_norms[db_norms == 0] = 1e-10
        if query_norm == 0:
            query_norm = 1e-10
            
        scores = dot_products / (db_norms * query_norm)
        
        # Sort by highest score first
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_indices:
            results.append({
                "chunk": self.chunks[idx],
                "score": float(scores[idx])
            })
            
        return results

    def clear(self):
        """Clears the local database and deletes the file."""
        self.chunks = []
        self.embeddings = []
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def save(self):
        """Persists the database to disk."""
        data = {
            "chunks": self.chunks,
            "embeddings": self.embeddings
        }
        with open(self.db_path, "w") as f:
            json.dump(data, f)

    def load(self):
        """Loads database from disk if it exists."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    self.chunks = data.get("chunks", [])
                    self.embeddings = data.get("embeddings", [])
            except Exception:
                self.chunks = []
                self.embeddings = []
