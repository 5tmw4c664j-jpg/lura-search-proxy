"""
LURA Image Search Proxy
DuckDuckGo image search with Wikimedia Commons fallback.
"""
import os
import urllib.request
import urllib.parse
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from duckduckgo_search import DDGS
import uvicorn

class SearchRequest(BaseModel):
    query: str = ""
    count: int = 8

app = FastAPI(title="LURA Search Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://duckduckgo.com/",
}

def search_wikimedia(query: str, count: int) -> list:
    url = (
        "https://commons.wikimedia.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": min(count, 50),
            "format": "json",
            "origin": "*",
        })
    )
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    results = []
    for page in data.get("query", {}).get("search", []):
        title = page.get("title", "")
        image_url = (
            "https://commons.wikimedia.org/wiki/Special:FilePath/"
            + urllib.parse.quote(title.replace(" ", "_"))
            + "?width=800"
        )
        thumb_url = (
            "https://commons.wikimedia.org/wiki/Special:FilePath/"
            + urllib.parse.quote(title.replace(" ", "_"))
            + "?width=300"
        )
        results.append({
            "title": title,
            "url": image_url,
            "thumbnail": thumb_url,
        })
    return results

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/search")
async def search_images(req: SearchRequest):
    if not req.query:
        return {"success": False, "results": [], "error": "No query provided"}
    
    # Try DuckDuckGo first
    try:
        results = []
        with DDGS(headers=HEADERS) as ddgs:
            for r in ddgs.images(keywords=req.query, max_results=req.count):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("image", ""),
                    "thumbnail": r.get("thumbnail", ""),
                })
        if results:
            return {"success": True, "source": "duckduckgo", "results": results}
    except Exception as e:
        ddg_error = str(e)

    # Fallback to Wikimedia Commons
    try:
        results = search_wikimedia(req.query, req.count)
        if results:
            return {"success": True, "source": "wikimedia", "results": results}
    except Exception as e:
        return {
            "success": False,
            "results": [],
            "error": f"DDG: {ddg_error}; Wikimedia: {str(e)}",
        }

    return {"success": False, "results": [], "error": "No results found"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
