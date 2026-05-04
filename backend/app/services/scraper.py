import re
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

async def scrape_job_description(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            html = response.text
    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Could not extract job description from this URL. Please paste the job description manually."
        )

    soup = BeautifulSoup(html, "lxml")
    
    # Remove navigation/footer noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
        
    text = ""
    
    # 1. <div> or <section> with class/id containing specific keywords
    keywords = ["job-description", "description", "details", "jobDescription", "job_description"]
    
    def match_element(tag):
        if tag.name not in ["div", "section"]:
            return False
            
        classes = tag.get("class", [])
        if isinstance(classes, str):
            classes = [classes]
        
        tag_id = tag.get("id", "")
        
        # Check both class names and ID
        attributes_to_check = classes + [tag_id]
        
        for val in attributes_to_check:
            val_lower = val.lower()
            for kw in keywords:
                if kw.lower() in val_lower:
                    return True
        return False

    element = soup.find(match_element)
    if element:
        text = element.get_text(separator=" ", strip=True)
        
    # 2. Fall back to main content area
    if len(text) < 100:
        main_element = soup.find("main") or soup.find("article")
        if main_element:
            text = main_element.get_text(separator=" ", strip=True)
            
    # 3. Fall back to body text
    if len(text) < 100:
        body_element = soup.find("body")
        if body_element:
            text = body_element.get_text(separator=" ", strip=True)
            
    # Clean extracted text - remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    if len(text) < 100:
        raise HTTPException(
            status_code=422,
            detail="Could not extract job description from this URL. Please paste the job description manually."
        )
        
    return text
