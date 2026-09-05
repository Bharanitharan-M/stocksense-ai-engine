from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import httpx
import logging
import os

from src.pipelines.ai_engine import run_full_pipeline, run_discovery_pipeline
from src.models.schemas import AIAnalysisResponse, DiscoveryOutput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/engine", tags=["AI Engine"])

class ProcessDocumentRequest(BaseModel):
    transaction_id: str
    headline: str
    content: str

class DiscoverQueryRequest(BaseModel):
    query: str

class DiscoverAsyncRequest(BaseModel):
    query: str
    userEmails: List[str]
    top_url: str

def process_discovery_background(query: str, user_emails: List[str], top_url: str):
    try:
        import uuid
        transaction_id = "disc-" + uuid.uuid4().hex[:8]
        result = run_discovery_pipeline(
            transaction_id=transaction_id,
            query=query
        )
        
        # Prepare payload for Webhook
        payload = result.dict()
        payload["query"] = query
        payload["userEmails"] = user_emails
        payload["top_url"] = top_url
        
        # Call Java Webhook
        base_url = os.getenv("JAVA_BACKEND_URL", "https://stocksense-backend-3w34.onrender.com")
        webhook_url = f"{base_url}/api/v1/internal/webhook/insight-result"
        with httpx.Client(timeout=30.0) as client:
            client.post(webhook_url, json=payload)
            logger.info(f"Successfully sent async discovery result to Java for {query}")
            
    except Exception as e:
        logger.error(f"Background discovery failed for {query}: {e}")
        # Send failure payload
        try:
            payload = {
                "query": query,
                "userEmails": user_emails,
                "top_url": top_url,
                "relevance_outcome": "NOT_RELEVANT"
            }
            with httpx.Client(timeout=30.0) as client:
                base_url = os.getenv("JAVA_BACKEND_URL", "https://stocksense-backend-3w34.onrender.com")
                webhook_url = f"{base_url}/api/v1/internal/webhook/insight-result"
                client.post(webhook_url, json=payload)
        except Exception:
            pass

@router.post("/process", response_model=AIAnalysisResponse)
async def process_document(request: ProcessDocumentRequest):
    """
    Ingests a raw financial document and runs it through the 3-stage AI Pipeline.
    Returns structured JSON ready for the Java Orchestrator.
    """
    try:
        result = run_full_pipeline(
            transaction_id=request.transaction_id,
            source_headline=request.headline,
            source_content=request.content
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/discover", response_model=DiscoveryOutput)
async def discover_query(request: DiscoverQueryRequest):
    """
    Triggers live search grounding and extracts structured financial insight on-demand.
    """
    try:
        import uuid
        transaction_id = "disc-" + uuid.uuid4().hex[:8]
        result = run_discovery_pipeline(
            transaction_id=transaction_id,
            query=request.query
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/discover-async", status_code=202)
async def discover_query_async(request: DiscoverAsyncRequest, background_tasks: BackgroundTasks):
    """
    Fire and forget async discovery to prevent HTTP timeouts.
    """
    background_tasks.add_task(
        process_discovery_background, 
        request.query, 
        request.userEmails, 
        request.top_url
    )
    return {"message": "Accepted for processing"}
