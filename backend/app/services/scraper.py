import json
import re
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
from fastapi import HTTPException
import trafilatura

async def scrape_job_description(url: str) -> str:
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    html = ""
    try:
        # Tier 1: Fast HTTP Extraction with curl_cffi (mimics Chrome to bypass basic blocks)
        async with AsyncSession(impersonate="chrome", timeout=15.0) as session:
            response = await session.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
    except Exception:
        # Tier 3: Graceful Fallback if blocked (e.g. LinkedIn 403)
        raise HTTPException(
            status_code=422,
            detail="Could not extract job description from this URL. Please paste the job description manually."
        )

    if not html:
        raise HTTPException(
            status_code=422,
            detail="Could not extract job description from this URL. Please paste the job description manually."
        )

    soup = BeautifulSoup(html, "lxml")
    text = ""

    # Strategy 1: JSON-LD (Most accurate, structured data provided by Greenhouse/Lever/etc.)
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    for script in json_ld_scripts:
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            # JSON-LD can be a list or a dict
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        text = item.get("description", "")
                        break
            elif isinstance(data, dict):
                if data.get("@type") == "JobPosting":
                    text = data.get("description", "")
                    
            if text:
                # The description in JSON-LD often contains HTML tags
                clean_text = BeautifulSoup(text, "lxml").get_text(separator=" ", strip=True)
                if len(clean_text) > 100:
                    text = clean_text
                    break
        except (json.JSONDecodeError, TypeError):
            continue

    # Strategy 2: Trafilatura Fallback (Excellent for extracting main content)
    if len(text) < 100:
        extracted = trafilatura.extract(html, include_links=False, include_images=False, include_tables=True)
        if extracted:
            text = extracted

    # Strategy 3: Basic BeautifulSoup Fallback (if trafilatura fails entirely)
    if len(text) < 100:
        # Remove navigation/footer noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
            
        main_element = soup.find("main") or soup.find("article") or soup.find("body")
        if main_element:
            text = main_element.get_text(separator=" ", strip=True)
            
    # Clean extracted text - remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) < 100:
        raise HTTPException(
            status_code=422,
            detail="Could not extract job description from this URL. Please paste the job description manually."
        )
        
    return text
