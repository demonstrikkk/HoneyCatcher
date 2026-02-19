"""Testing endpoints for development and debugging."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


class TestURLRequest(BaseModel):
    """Request model for URL testing."""
    urls: List[str]


class URLScanResult(BaseModel):
    """URL scan result model."""
    url: str
    is_safe: bool
    risk_score: float
    findings: List[str]
    scanner_results: dict


@router.post("/test-virustotal")
async def test_virustotal(request: TestURLRequest):
    """
    Test VirusTotal URL scanning with provided URLs.
    
    Example malicious URLs to test:
    - http://malware.testing.google.test/testing/malware/
    - https://www.eicar.org/download/eicar.com.txt
    - http://testsafebrowsing.appspot.com/s/malware.html
    
    Args:
        request: TestURLRequest with list of URLs to scan
        
    Returns:
        List of scan results with risk scores and findings
    """
    try:
        logger.info(f"🧪 Testing VirusTotal with {len(request.urls)} URLs: {request.urls}")
        
        from features.live_takeover.url_scanner import url_scanner
        
        # Scan all URLs
        results = await url_scanner.scan_urls(request.urls)
        
        # Format results
        formatted_results = []
        for result in results:
            logger.info(f"📊 Scan result for {result.url}: "
                       f"Safe={result.is_safe}, Risk={result.risk_score:.2f}, "
                       f"Findings={len(result.findings)}")
            
            formatted_results.append({
                "url": result.url,
                "is_safe": result.is_safe,
                "risk_score": result.risk_score,
                "findings": result.findings,
                "scanner_results": result.scanner_results,
                "summary": f"{'✅ SAFE' if result.is_safe else '⚠️ MALICIOUS'} - Risk: {result.risk_score:.1%}"
            })
        
        logger.info(f"✅ Completed VirusTotal test for {len(formatted_results)} URLs")
        
        return {
            "success": True,
            "total_urls": len(request.urls),
            "results": formatted_results,
            "test_urls": {
                "malicious_samples": [
                    "http://malware.testing.google.test/testing/malware/",
                    "https://www.eicar.org/download/eicar.com.txt",
                    "http://testsafebrowsing.appspot.com/s/malware.html"
                ],
                "safe_samples": [
                    "https://www.google.com",
                    "https://www.github.com"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ VirusTotal test failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"VirusTotal test failed: {str(e)}")


@router.get("/test-virustotal/info")
async def virustotal_info():
    """
    Get information about VirusTotal configuration and test URLs.
    """
    from config import settings
    
    has_api_key = bool(getattr(settings, 'VIRUSTOTAL_API_KEY', None))
    
    return {
        "virustotal_configured": has_api_key,
        "api_key_set": has_api_key,
        "test_urls": {
            "malicious": [
                {
                    "url": "http://malware.testing.google.test/testing/malware/",
                    "description": "Google Safe Browsing test URL for malware"
                },
                {
                    "url": "https://www.eicar.org/download/eicar.com.txt",
                    "description": "EICAR anti-malware test file"
                },
                {
                    "url": "http://testsafebrowsing.appspot.com/s/malware.html",
                    "description": "Google Safe Browsing test page"
                }
            ],
            "safe": [
                {
                    "url": "https://www.google.com",
                    "description": "Google homepage (safe)"
                },
                {
                    "url": "https://www.github.com",
                    "description": "GitHub homepage (safe)"
                }
            ]
        },
        "usage": {
            "endpoint": "/api/test-virustotal",
            "method": "POST",
            "body": {
                "urls": ["http://example.com"]
            }
        }
    }
