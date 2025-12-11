from __future__ import annotations

import os
import asyncio
import httpx
from typing import List, Dict, Any

from .async_circuit_breaker import get_breaker

MATH_CORE_URL = os.getenv("MATH_CORE_URL", "http://math-core:8004")
TIMEOUT = float(os.getenv("MATH_CORE_TIMEOUT", "5"))


class MathCoreClient:
    def __init__(self, base_url: str = MATH_CORE_URL):
        self.base = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.breaker = get_breaker("math-core")

    async def cost_per_token(self, price_per_hour: float, gpu_type: str) -> Dict[str, Any] | None:
        payload = {
            "price_per_hour": price_per_hour,
            "gpu_type": gpu_type,
            "model_size": "7b",
        }
        try:
            resp = await self.breaker.call(
                self.client.post, f"{self.base}/math/cost-per-token", json=payload
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    async def cost_per_gflop(self, price_per_hour: float, gpu_type: str) -> Dict[str, Any] | None:
        payload = {
            "price_per_hour": price_per_hour,
            "gpu_type": gpu_type,
        }
        try:
            resp = await self.breaker.call(
                self.client.post, f"{self.base}/math/cost-per-gflop", json=payload
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    async def enrich_offers(self, offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        async def enrich_one(o: Dict[str, Any]) -> Dict[str, Any]:
            gpu = o.get("gpu") or o.get("gpu_type") or ""
            price = o.get("price_per_hour")
            if not gpu or price is None:
                return o
            cpt = await self.cost_per_token(price, gpu)
            cpg = await self.cost_per_gflop(price, gpu)
            enriched = dict(o)
            if cpt:
                enriched["cost_per_token"] = cpt.get("cost_per_token")
                enriched["cost_per_million_tokens"] = cpt.get("cost_per_million_tokens")
            if cpg:
                enriched["cost_per_gflop"] = cpg.get("cost_per_gflop")
            return enriched

        return await asyncio.gather(*[enrich_one(o) for o in offers])

    async def close(self):
        await self.client.aclose()
