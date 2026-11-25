from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import time

from app.rag import rag_service

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base & RAG"])

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, description="Question or keyword to search in FAISS")
    top_k: int = Field(3, ge=1, le=10)

@router.get("/chunks")
async def get_all_chunks():
    """
    Returns all indexed knowledge base chunks for live UI demonstration.
    """
    chunks = rag_service.get_all_chunks()
    return {
        "total_chunks": len(chunks),
        "embedding_model": rag_service.model_name,
        "vector_dimension": rag_service.dimension,
        "chunks": chunks
    }

@router.post("/search")
async def search_knowledge(req: SearchQuery):
    """
    Interactive endpoint to test FAISS cosine similarity retrieval.
    Shows the exact retrieved context and similarity scores for demonstration.
    """
    start_time = time.time()
    results = rag_service.search(req.query, top_k=req.top_k)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "query": req.query,
        "retrieved_count": len(results),
        "latency_ms": duration_ms,
        "results": results
    }
