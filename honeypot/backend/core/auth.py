from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from config import settings

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Validates the x-api-key header.
    """
    if not api_key:
         raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Missing x-api-key header"
        )
    
    if api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Invalid API Key"
        )
    return api_key
