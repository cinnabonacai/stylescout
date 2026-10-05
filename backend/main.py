"""
main.py

FastAPI backend for StyleScout.

Wraps the existing LangGraph agent (agent/graph.py) behind a small REST
API so a real frontend (frontend/) can talk to it, instead of the
agent being embedded directly inside a Streamlit script. The agent
logic itself is unchanged -- this file is purely a thin HTTP layer.

Run with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.graph import run_styling_request


app = FastAPI(title="StyleScout API")

# Local dev origins for Vite (default 5173) and Create-React-App style
# (3000), plus a wildcard fallback so this doesn't block early
# development. Tighten this to your real frontend domain when deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class StyleRequest(BaseModel):
    query: str


class CatalogItem(BaseModel):
    item_id: int
    name: str
    category: str
    color: str
    style_tags: str
    season: str
    price: float
    brand: str
    relevance: float


class TrendNote(BaseModel):
    trend_id: str
    excerpt: str
    relevance: float


class StyleResponse(BaseModel):
    query: str
    search_query: str
    budget: float | None
    styling_notes: str
    critique: str
    selected_items: list[CatalogItem]
    total_cost: float
    fits_budget: bool | None
    catalog_results: list[CatalogItem]
    trend_results: list[TrendNote]


@app.get("/api/health")
def health() -> dict:
    """Simple liveness check the frontend can ping on load."""
    return {"status": "ok"}


@app.post("/api/style", response_model=StyleResponse)
def style(request: StyleRequest) -> StyleResponse:
    """
    Run a styling request through the full LangGraph agent
    (planner -> retriever -> stylist -> critic) and return the result.
    """

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    result = run_styling_request(request.query)

    return StyleResponse(
        query=result["query"],
        search_query=result["search_query"],
        budget=result.get("budget"),
        styling_notes=result["final_output"],
        critique=result["critique"],
        selected_items=result["selected_items"],
        total_cost=result["total_cost"],
        fits_budget=result.get("fits_budget"),
        catalog_results=result["catalog_results"],
        trend_results=result["trend_results"],
    )
