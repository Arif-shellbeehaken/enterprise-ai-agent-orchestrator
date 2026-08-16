"""
Tool adapters for external systems (Salesforce, ERP, generic REST webhooks).
In production these would contain real OAuth / API clients.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class ToolsAdapter:
    """Lightweight integration layer for external write operations."""

    def __init__(self, tenant_id: UUID, timeout: float = 30.0):
        self.tenant_id = tenant_id
        self.timeout = timeout

    async def execute_rest_webhook(
        self,
        url: str,
        method: str = "POST",
        payload: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generic authenticated REST call."""
        headers = headers or {"Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text}
            return {
                "status_code": response.status_code,
                "body": body,
                "success": True,
            }

    async def salesforce_update(
        self,
        object_type: str,
        record_id: str,
        fields: Dict[str, Any],
        instance_url: str,
        access_token: str,
    ) -> Dict[str, Any]:
        """Placeholder Salesforce update (requires real credentials)."""
        url = f"{instance_url}/services/data/v59.0/sobjects/{object_type}/{record_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        return await self.execute_rest_webhook(
            url=url, method="PATCH", payload=fields, headers=headers
        )

    async def erp_write(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        api_key: str,
    ) -> Dict[str, Any]:
        """Placeholder ERP write operation."""
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        return await self.execute_rest_webhook(
            url=endpoint, method="POST", payload=payload, headers=headers
        )

    async def estimate_cost_usd(self, action: str, payload: Optional[Dict] = None) -> float:
        """
        Rough cost estimator used by the Human Approval Gate.
        In production this would query pricing tables or token counters.
        """
        # Simple heuristic
        if "payout" in action.lower() or "payment" in action.lower():
            amount = float((payload or {}).get("amount", 0))
            return amount
        if "database" in action.lower() or "update" in action.lower():
            return 25.0  # arbitrary sensitive-write cost
        return 5.0
