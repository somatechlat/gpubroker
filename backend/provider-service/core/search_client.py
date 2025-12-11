from __future__ import annotations

import os
import httpx
from typing import Dict, Any

MEILI_URL = os.getenv("MEILISEARCH_URL", "")
MEILI_KEY = os.getenv("MEILISEARCH_API_KEY", "")
INDEX = os.getenv("MEILISEARCH_INDEX", "offers")
TIMEOUT = float(os.getenv("MEILISEARCH_TIMEOUT", "2"))


class MeiliSearchClient:
    def __init__(self, base_url: str = MEILI_URL):
        self.base = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=TIMEOUT)

    async def search_offers(self, query: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        if not self.base:
            return {}
        headers = {"X-Meili-API-Key": MEILI_KEY} if MEILI_KEY else {}
        payload = {"q": query, "limit": limit, "offset": offset}
        resp = await self.client.post(f"{self.base}/indexes/{INDEX}/search", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()
