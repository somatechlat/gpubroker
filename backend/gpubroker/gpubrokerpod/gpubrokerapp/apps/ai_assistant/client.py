"""
SomaAgent Client.

Async HTTP client for communicating with SomaAgent LLM service.
NO MOCKS. NO FAKE DATA. REAL API CALLS ONLY.
"""
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger('gpubroker.ai_assistant.client')

# Configuration from environment
SOMA_BASE = os.getenv("SOMA_AGENT_BASE", "")
SOMA_TIMEOUT = float(os.getenv("SOMA_AGENT_TIMEOUT", "30"))


class SomaAgentClient:
    """
    Async client for SomaAgent LLM service.
    
    Provides methods for:
    - invoke: Send messages to LLM
    - get_session_history: Retrieve conversation history
    - list_tools: List available tools
    - health: Check service health
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = SOMA_TIMEOUT
    ):
        self.base = (base_url or SOMA_BASE).rstrip("/")
        if not self.base:
            raise ValueError("SOMA_AGENT_BASE must be set")
        self.timeout = timeout
        self._session: Optional[httpx.AsyncClient] = None
    
    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session."""
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(timeout=self.timeout)
        return self._session
    
    async def invoke(
        self,
        messages: List[Dict[str, str]],
        session_id: Optional[str] = None,
        tenant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Invoke LLM with messages.
        
        Args:
            messages: List of {role, content} message dicts
            session_id: Optional session identifier for history
            tenant: Optional tenant identifier
        
        Returns:
            LLM response dict with content/reply
        """
        session = await self._get_session()
        
        payload: Dict[str, Any] = {"messages": messages}
        if session_id:
            payload["session_id"] = session_id
        if tenant:
            payload["tenant"] = tenant
        
        try:
            resp = await session.post(f"{self.base}/v1/llm/invoke", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"SomaAgent invoke failed: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            logger.error(f"SomaAgent request error: {e}")
            raise
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of history items
        
        Returns:
            Dict with history items
        """
        session = await self._get_session()
        
        try:
            resp = await session.get(
                f"{self.base}/v1/sessions/{session_id}/history",
                params={"limit": limit}
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Session history fetch failed: {e.response.status_code}")
            raise
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available LLM tools."""
        session = await self._get_session()
        
        try:
            resp = await session.get(f"{self.base}/v1/tools")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"List tools failed: {e.response.status_code}")
            raise
    
    async def health(self) -> Dict[str, Any]:
        """Check SomaAgent health."""
        session = await self._get_session()
        
        try:
            resp = await session.get(f"{self.base}/v1/health")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Health check failed: {e.response.status_code}")
            raise
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.is_closed:
            await self._session.aclose()
            self._session = None
