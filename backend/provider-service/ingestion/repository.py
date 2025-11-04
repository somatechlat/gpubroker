from __future__ import annotations

from typing import List, Dict, Optional
from datetime import datetime

from ..db import get_pool


class OfferRepository:
    async def ensure_provider(
        self, name: str, display_name: str, api_base_url: str
    ) -> str:
        """Ensure a provider row exists and return its id (UUID as str)."""
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM providers WHERE name = $1",
                name,
            )
            if row:
                return str(row["id"])
            row = await conn.fetchrow(
                """
                INSERT INTO providers (name, display_name, api_base_url)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                name,
                display_name or name,
                api_base_url,
            )
            return str(row["id"])  # type: ignore

    async def upsert_offers(
        self,
        provider_id: str,
        offers: List[Dict],
    ) -> int:
        """Upsert normalized offers into gpu_offers and append to price_history.
        Each offer dict requires: external_id, gpu_type, gpu_memory_gb, cpu_cores,
        ram_gb, storage_gb, price_per_hour, currency, region, availability_status, compliance_tags
        """
        if not offers:
            return 0
        pool = get_pool()
        total = 0
        async with pool.acquire() as conn:
            async with conn.transaction():
                for o in offers:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO gpu_offers (
                          provider_id, external_id, gpu_type, gpu_memory_gb, cpu_cores, ram_gb,
                          storage_gb, price_per_hour, currency, region, availability_status,
                          compliance_tags, last_seen_at
                        ) VALUES (
                          $1, $2, $3, $4, $5, $6,
                          $7, $8, $9, $10, $11,
                          $12, NOW()
                        )
                        ON CONFLICT (provider_id, external_id) DO UPDATE SET
                          gpu_type = EXCLUDED.gpu_type,
                          gpu_memory_gb = EXCLUDED.gpu_memory_gb,
                          cpu_cores = EXCLUDED.cpu_cores,
                          ram_gb = EXCLUDED.ram_gb,
                          storage_gb = EXCLUDED.storage_gb,
                          price_per_hour = EXCLUDED.price_per_hour,
                          currency = EXCLUDED.currency,
                          region = EXCLUDED.region,
                          availability_status = EXCLUDED.availability_status,
                          compliance_tags = EXCLUDED.compliance_tags,
                          updated_at = NOW(),
                          last_seen_at = NOW()
                        RETURNING id, price_per_hour, availability_status
                        """,
                        provider_id,
                        o["external_id"],
                        o.get("gpu_type"),
                        o.get("gpu_memory_gb", 0),
                        o.get("cpu_cores", 0),
                        o.get("ram_gb", 0),
                        o.get("storage_gb", 0),
                        o.get("price_per_hour", 0.0),
                        o.get("currency", "USD"),
                        o.get("region", "unknown"),
                        o.get("availability_status", "available"),
                        o.get("compliance_tags", []),
                    )
                    offer_id = row["id"]
                    await conn.execute(
                        """
                        INSERT INTO price_history (offer_id, price_per_hour, availability_status)
                        VALUES ($1, $2, $3)
                        """,
                        offer_id,
                        row["price_per_hour"],
                        row["availability_status"],
                    )
                    total += 1
        return total

    async def list_offers(
        self,
        *,
        gpu_term: Optional[str] = None,
        region: Optional[str] = None,
        max_price: Optional[float] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict:
        """Query offers with filters and pagination from gpu_offers joined with providers.
        Returns a dict: { total: int, items: List[Dict] }
        """
        pool = get_pool()
        where = ["1=1"]
        params: List = []

        if gpu_term:
            where.append(
                "(go.gpu_type ILIKE $%d OR go.external_id ILIKE $%d)"
                % (len(params) + 1, len(params) + 2)
            )
            like = f"%{gpu_term}%"
            params.extend([like, like])
        if region:
            where.append("go.region = $%d" % (len(params) + 1))
            params.append(region)
        if max_price is not None:
            where.append("go.price_per_hour <= $%d" % (len(params) + 1))
            params.append(max_price)

        where_sql = " AND ".join(where)
        offset = (page - 1) * per_page

        async with pool.acquire() as conn:
            total = await conn.fetchval(
                f"""
                SELECT COUNT(*)
                FROM gpu_offers go
                WHERE {where_sql}
                """,
                *params,
            )

            rows = await conn.fetch(
                f"""
                SELECT 
                  p.name AS provider_name,
                  go.external_id,
                  go.gpu_type,
                  go.price_per_hour,
                  go.region,
                  go.availability_status,
                  go.compliance_tags,
                  go.updated_at
                FROM gpu_offers go
                JOIN providers p ON p.id = go.provider_id
                WHERE {where_sql}
                ORDER BY go.price_per_hour ASC, go.updated_at DESC
                OFFSET $%d LIMIT $%d
                """
                % (len(params) + 1, len(params) + 2),
                *params,
                offset,
                per_page,
            )

        items: List[Dict] = []
        for r in rows:
            items.append(
                {
                    "id": f"{r['provider_name']}:{r['external_id']}:{r['region']}",
                    "name": r["gpu_type"],
                    "gpu": r["gpu_type"],
                    "price_per_hour": float(r["price_per_hour"]),
                    "availability": r["availability_status"],
                    "region": r["region"],
                    "provider": r["provider_name"],
                    "tags": r["compliance_tags"] or [],
                    "last_updated": r["updated_at"].isoformat()
                    if r["updated_at"]
                    else datetime.utcnow().isoformat(),
                }
            )

        return {"total": int(total or 0), "items": items}
