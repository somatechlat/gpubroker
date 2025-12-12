"""
AI Assistant Service gateway to SomaAgent.
Requires valid LLM credentials; current implementation proxies tools and parses workloads without mock responses.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import logging
import time
import httpx
from contextlib import asynccontextmanager

from client import SomaAgentClient

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "somagent")
SOMA_BASE = os.getenv("SOMA_AGENT_BASE")
PROVIDER_API_URL = os.getenv("PROVIDER_API_URL", "http://provider-service:8000")
MATH_CORE_URL = os.getenv("MATH_CORE_URL", "http://math-core:8004")
MAX_HISTORY_TURNS = int(os.getenv("AI_MAX_HISTORY_TURNS", "10"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not SOMA_BASE:
        raise RuntimeError("SOMA_AGENT_BASE must be set (no hardcoded defaults allowed)")
    yield


app = FastAPI(title="GPUBROKER AI Assistant", version="0.1.0", docs_url="/docs", lifespan=lifespan)


class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    context: Dict[str, Any] = {}
    history: List[Dict[str, str]] = []  # [{role, content}]


class ChatResponse(BaseModel):
    reply: str
    sources: Optional[List[str]] = None
    elapsed_ms: float
    recommendations: Optional[List[Dict[str, Any]]] = None
    session_history: Optional[List[Dict[str, Any]]] = None


@app.post("/ai/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start = time.time()
    client = SomaAgentClient(base_url=SOMA_BASE)
    recommendations: Optional[List[Dict[str, Any]]] = None
    history_payload: Optional[List[Dict[str, Any]]] = None
    rec_data: Dict[str, Any] = {}
    try:
        trimmed_history = req.history[-MAX_HISTORY_TURNS:] if req.history else []
        messages = trimmed_history + [{"role": "user", "content": req.message}]
        result = await client.invoke(
            messages=messages,
            session_id=req.user_id,
            tenant=None,
        )
        reply = result.get("content") or result.get("reply") or ""
        # hydrate server-side history if a session_id exists
        if req.user_id:
            try:
                hist = await client.get_session_history(req.user_id, limit=50)
                history_payload = hist.get("items") if isinstance(hist, dict) else hist
            except Exception as hist_err:
                logger.warning("Session history fetch failed: %s", hist_err)

        # Optional: fetch candidate offers and ask Math Core for ensemble recommendations
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                filters = req.context.get("filters", {}) if req.context else {}
                params = {"per_page": 20, **filters}
                prov_resp = await http.get(f"{PROVIDER_API_URL}/providers", params=params)
                prov_resp.raise_for_status()
                items = prov_resp.json().get("items", [])
                candidate_offers = []
                for it in items[:20]:
                    candidate_offers.append(
                        {
                            "price_per_hour": it.get("price_per_hour"),
                            "gpu": it.get("gpu") or it.get("name"),
                            "provider": it.get("provider"),
                            "region": it.get("region"),
                            "availability": it.get("availability"),
                            "compliance_tags": it.get("tags", []),
                            "gpu_memory_gb": it.get("gpu_memory_gb"),
                        }
                    )
                if candidate_offers:
                    payload = {
                        "user_id": req.user_id,
                        "workload_profile": req.context.get("workload_profile", {}) if req.context else {},
                        "candidate_offers": candidate_offers,
                        "top_k": 5,
                    }
                    rec_resp = await http.post(f"{MATH_CORE_URL}/math/ensemble-recommend", json=payload)
                    rec_resp.raise_for_status()
                    rec_data = rec_resp.json()
                recommendations = rec_data.get("recommendations", []) if rec_data else None
        except Exception as rec_err:
            logger.warning("Recommendation enrichment failed: %s", rec_err)

        elapsed_ms = (time.time() - start) * 1000
        return ChatResponse(
            reply=reply,
            sources=None,
            elapsed_ms=elapsed_ms,
            recommendations=recommendations,
            session_history=history_payload,
        )
    except Exception as e:
        logger.error("somagent invoke failed: %s", e)
        raise HTTPException(status_code=502, detail="AI agent call failed")
    finally:
        await client.close()


@app.get("/ai/sessions/{session_id}/history")
async def get_history(session_id: str, limit: int = 50):
    client = SomaAgentClient(base_url=SOMA_BASE)
    try:
        return await client.get_session_history(session_id, limit=limit)
    finally:
        await client.close()


@app.get("/ai/tools")
async def list_tools():
    client = SomaAgentClient(base_url=SOMA_BASE)
    try:
        return await client.list_tools()
    finally:
        await client.close()


@app.get("/ai/health")
async def agent_health():
    client = SomaAgentClient(base_url=SOMA_BASE)
    try:
        return await client.health()
    finally:
        await client.close()


class ParseWorkloadRequest(BaseModel):
    text: str


class ParsedWorkload(BaseModel):
    workload_type: str
    quantity: Optional[int] = None
    duration: Optional[str] = None
    region: Optional[str] = None
    quality: Optional[str] = None


@app.post("/ai/parse-workload", response_model=ParsedWorkload)
async def parse_workload(req: ParseWorkloadRequest):
    text = req.text.lower()
    workload_type = "llm_inference" if "token" in text or "chat" in text else "image_generation"
    return ParsedWorkload(workload_type=workload_type)


@app.get("/health")
async def health():
    return {"status": "ok", "llm_provider": LLM_PROVIDER}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006, reload=True)
