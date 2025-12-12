from __future__ import annotations

import os
import httpx
from typing import List, Dict, Any, Optional

SOMA_BASE = os.getenv("SOMA_AGENT_BASE")
if not SOMA_BASE:
    raise RuntimeError("SOMA_AGENT_BASE must be set (no hardcoded defaults allowed)")
SOMA_TIMEOUT = float(os.getenv("SOMA_AGENT_TIMEOUT", "30"))
SOMA_STREAM_TIMEOUT = float(os.getenv("SOMA_AGENT_STREAM_TIMEOUT", "60"))
SOMA_TOOLS_INDEX = os.getenv("SOMA_AGENT_TOOLS_INDEX", "offers")


class SomaAgentClient:
    def __init__(self, base_url: str = SOMA_BASE, timeout: float = SOMA_TIMEOUT):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = httpx.AsyncClient(timeout=self.timeout)

    async def invoke(self, messages: List[Dict[str, str]], session_id: str | None = None, tenant: str | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"messages": messages}
        if session_id:
            payload["session_id"] = session_id
        if tenant:
            payload["tenant"] = tenant
        resp = await self.session.post(f"{self.base}/v1/llm/invoke", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_session_history(self, session_id: str, limit: int = 50) -> Dict[str, Any]:
        resp = await self.session.get(f"{self.base}/v1/sessions/{session_id}/history", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()

    async def list_tools(self) -> Dict[str, Any]:
        resp = await self.session.get(f"{self.base}/v1/tools")
        resp.raise_for_status()
        return resp.json()

    async def health(self) -> Dict[str, Any]:
        resp = await self.session.get(f"{self.base}/v1/health")
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.session.aclose()
