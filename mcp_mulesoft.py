#!/usr/bin/env python3
"""
MCP Server for MuleSoft Integration
Provides tools to interact with MuleSoft SAP integration
"""

import json
import httpx
from typing import Optional
from mcp.server import Server
from mcp.types import TextContent

API_BASE_URL = "http://localhost:8000"
DEFAULT_TOKEN = None

server = Server("mulesoft-integration")


def set_token(token: str):
    global DEFAULT_TOKEN
    DEFAULT_TOKEN = token


async def api_call(
    method: str,
    endpoint: str,
    data: Optional[dict] = None,
    token: Optional[str] = None,
    params: Optional[dict] = None,
) -> dict:
    headers = {"Content-Type": "application/json"}
    if token or DEFAULT_TOKEN:
        headers["Authorization"] = f"Bearer {token or DEFAULT_TOKEN}"

    url = f"{API_BASE_URL}{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            response = await client.get(url, headers=headers, params=params)
        elif method == "POST":
            response = await client.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = await client.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        if response.status_code >= 400:
            return {
                "error": f"API Error {response.status_code}",
                "details": response.text,
            }
        return response.json()


# ============================================================================
# MULESOFT INTEGRATION TOOLS
# ============================================================================

@server.call_tool()
async def sync_case_to_sap(case_id: int, operation: str = "CREATE"):
    """Synchronize a case to SAP via MuleSoft"""
    result = await api_call(
        "POST",
        "/api/sap-integration/cases/sync",
        {"case_id": case_id, "operation": operation},
    )
    return [TextContent(type="text", text=json.dumps(result))]


@server.call_tool()
async def sync_cases_batch(case_ids: list, operation: str = "CREATE"):
    """Batch synchronize multiple cases to SAP"""
    result = await api_call(
        "POST",
        "/api/sap-integration/cases/sync-batch",
        {"case_ids": case_ids, "operation": operation},
    )
    return [TextContent(type="text", text=json.dumps(result))]


@server.call_tool()
async def get_case_sync_status(case_id: int):
    """Get synchronization status for a case"""
    result = await api_call("GET", f"/api/sap-integration/cases/{case_id}/sync-status")
    return [TextContent(type="text", text=json.dumps(result))]


@server.call_tool()
async def get_sap_case_status(sap_case_id: str):
    """Query case status from SAP"""
    result = await api_call(
        "POST",
        "/api/sap-integration/sap-cases/status",
        {"sap_case_id": sap_case_id},
    )
    return [TextContent(type="text", text=json.dumps(result))]


@server.call_tool()
async def trigger_auto_sync(case_id: int):
    """Trigger automatic synchronization for a case"""
    result = await api_call("GET", f"/api/sap-integration/cases/{case_id}/auto-sync")
    return [TextContent(type="text", text=json.dumps(result))]


@server.call_tool()
async def mulesoft_health_check():
    """Check MuleSoft integration health"""
    result = await api_call("GET", "/api/sap-integration/health")
    return [TextContent(type="text", text=json.dumps(result))]


@server.call_tool()
async def get_mulesoft_config():
    """Get MuleSoft integration configuration"""
    result = await api_call("GET", "/api/sap-integration/config")
    return [TextContent(type="text", text=json.dumps(result))]


if __name__ == "__main__":
    server.run()
