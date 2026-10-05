"""
mcp_server.py

StyleScout's custom MCP tool server.

This mirrors the MedSight pattern: instead of letting the agent call
Python functions directly, we expose a small set of tools behind the
Model Context Protocol so the agent (or any other MCP client) talks to
them over a standard interface. The three tools are:

  - catalog_search : search the structured product catalog
  - trend_lookup    : search the unstructured trend notes
  - budget_check    : validate whether a set of items fits a budget

Run it directly to serve over stdio:
    python tools/mcp_server.py

The LangGraph agent in agent/graph.py connects to this same server as
an MCP client, rather than importing these functions directly, so the
tool layer stays swappable (e.g. pointed at a real e-commerce API
later) without touching the agent logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this file directly (python tools/mcp_server.py) as well
# as importing it as a module from the project root.
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastmcp import FastMCP
from agent.retrieval import HybridIndex


mcp = FastMCP("stylescout-tools")

# Built once at import time and reused across tool calls — rebuilding
# the TF-IDF index on every call would be wasteful.
_index = HybridIndex()


@mcp.tool
def catalog_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Search the product catalog for items matching a style/occasion
    description.

    Args:
        query: free-text description, e.g. "cozy preppy fall top"
        top_k: how many items to return

    Returns:
        A list of catalog items with their metadata and a relevance score.
    """

    results = _index.search(query, top_k=top_k, source="catalog")

    return [
        {
            "item_id": r.metadata["item_id"],
            "name": r.metadata["name"],
            "category": r.metadata["category"],
            "color": r.metadata["color"],
            "style_tags": r.metadata["style_tags"],
            "season": r.metadata["season"],
            "price": r.metadata["price"],
            "brand": r.metadata["brand"],
            "relevance": round(r.score, 3),
        }
        for r in results
    ]


@mcp.tool
def trend_lookup(query: str, top_k: int = 3) -> list[dict]:
    """
    Search the fall/winter 2026 trend notes for context relevant to a
    styling request.

    Args:
        query: free-text description, e.g. "going out look"
        top_k: how many trend notes to return

    Returns:
        A list of trend note excerpts with a relevance score.
    """

    results = _index.search(query, top_k=top_k, source="trend_notes")

    return [
        {
            "trend_id": r.doc_id,
            "excerpt": r.text,
            "relevance": round(r.score, 3),
        }
        for r in results
    ]


@mcp.tool
def budget_check(item_ids: list[int], max_budget: float) -> dict:
    """
    Check whether a list of catalog item_ids fits within a budget.

    Args:
        item_ids: catalog item_id values to total up
        max_budget: the budget ceiling in dollars

    Returns:
        A dict with the item breakdown, total cost, whether it fits,
        and the amount over/under budget.
    """

    df = _index.catalog_df
    selected = df[df["item_id"].isin(item_ids)]

    total = float(selected["price"].sum())
    fits = total <= max_budget

    return {
        "items": selected[["item_id", "name", "price"]].to_dict(orient="records"),
        "total_cost": round(total, 2),
        "max_budget": max_budget,
        "fits_budget": fits,
        "difference": round(max_budget - total, 2),
    }


if __name__ == "__main__":
    mcp.run()
