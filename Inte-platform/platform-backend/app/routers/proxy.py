from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import httpx

router = APIRouter(prefix="/proxy", tags=["proxy"])

class ProxyRequest(BaseModel):
    url: str
    method: str = "GET"
    body: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None

@router.post("/request")
async def proxy_request(request: ProxyRequest):
    """Proxy requests to external services to avoid CORS issues"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            headers = request.headers or {}
            headers["Content-Type"] = "application/json"
            
            if request.method.upper() == "GET":
                response = await client.get(request.url, headers=headers)
            elif request.method.upper() == "POST":
                response = await client.post(request.url, json=request.body, headers=headers)
            elif request.method.upper() == "PUT":
                response = await client.put(request.url, json=request.body, headers=headers)
            elif request.method.upper() == "DELETE":
                response = await client.delete(request.url, headers=headers)
            elif request.method.upper() == "PATCH":
                response = await client.patch(request.url, json=request.body, headers=headers)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported method: {request.method}")
            
            # Try to parse JSON response, fallback to text
            try:
                data = response.json()
            except:
                data = response.text
            
            return {
                "status": response.status_code,
                "statusText": "OK" if response.status_code < 400 else "Error",
                "data": data
            }
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Service unavailable - cannot connect to target")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
