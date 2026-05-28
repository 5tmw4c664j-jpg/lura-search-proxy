"""
LURA DuckDuckGo Search Proxy
Minimal FastAPI service for DuckDuckGo image search.
"""
import os
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

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/search")
async def search_images(req: SearchRequest):
    if not req.query:
        return {"success": False, "results": [], "error": "No query provided"}
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.images(keywords=req.query, max_results=req.count):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("image", ""),
                    "thumbnail": r.get("thumbnail", ""),
                })
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "results": [], "error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
