"""
graph.py

StyleScout's LangGraph agent.

Mirrors the MedSight node structure (planner -> retriever ->
synthesizer -> self-critic), applied to outfit styling instead of
clinical research:

  planner    -> turns the raw user request into a clean search query
                 and an optional budget constraint
  retriever  -> calls the MCP tools (catalog_search, trend_lookup) to
                 pull grounding context
  stylist    -> picks a concrete set of item_ids from the retrieved
                 catalog results and writes short styling notes
  critic     -> calls the budget_check MCP tool to deterministically
                 verify the stylist's picks are actually in the
                 retrieved set and actually fit the budget (this is
                 not re-asking the LLM to check its own math -- it's a
                 real tool call against the catalog data), and either
                 approves the result or sends it back for one revision

The critic -> stylist loop runs at most once (bounded by
revision_count) so the graph always terminates quickly, which matters
for a live demo.
"""

from __future__ import annotations

import asyncio
import json
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from fastmcp import Client

from agent.llm import call_llm, strip_json_fences, has_real_provider
from tools.mcp_server import mcp


# ----------------------------------------------------------------------
# State
# ----------------------------------------------------------------------

class StyleScoutState(TypedDict):
    query: str                          # raw user request
    search_query: str                    # cleaned-up query for retrieval
    budget: Optional[float]               # extracted budget, if any
    catalog_results: list                  # from catalog_search tool
    trend_results: list                     # from trend_lookup tool
    selected_item_ids: list                  # stylist's picks (ints)
    styling_notes: str                        # stylist's short rationale
    critique: str                              # critic's notes
    needs_revision: bool                        # whether to loop back
    revision_count: int                          # guards against infinite loops
    selected_items: list                          # full item objects (final)
    total_cost: float                               # from budget_check tool
    fits_budget: Optional[bool]                      # from budget_check tool
    final_output: str                                 # styling_notes, approved


# ----------------------------------------------------------------------
# MCP tool call helper
# ----------------------------------------------------------------------

async def _call_tool_async(tool_name: str, args: dict):
    """Open a short-lived in-process MCP client session and call one tool."""

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, args)
        return result.data


def call_tool(tool_name: str, args: dict):
    """Sync wrapper -- LangGraph nodes here are plain sync functions."""

    return asyncio.run(_call_tool_async(tool_name, args))


# ----------------------------------------------------------------------
# Nodes
# ----------------------------------------------------------------------

def planner_node(state: StyleScoutState) -> dict:
    """
    Extract a clean search query and an optional budget number from the
    user's raw request, via a small structured LLM call.
    """

    system = (
        "You convert a shopper's styling request into JSON with two "
        "fields: 'search_query' (a short style/occasion description "
        "good for a search engine over a clothing catalog) and "
        "'budget' (a number in USD if the user mentioned one, else "
        "null). Respond with ONLY the JSON object, no other text."
    )

    try:
        # max_tokens is generous here on purpose: reasoning models (like
        # Groq's openai/gpt-oss-120b) spend some of this budget on
        # internal reasoning before writing the actual JSON, and a tight
        # budget combined with strict json_mode can make the provider
        # reject the call outright rather than return bad text -- so the
        # whole call, not just the parse, has to be inside this try.
        raw = call_llm(system=system, user=state["query"], max_tokens=300, json_mode=True)
        parsed = json.loads(strip_json_fences(raw))
        search_query = parsed.get("search_query") or state["query"]
        budget = parsed.get("budget")
    except Exception:
        # Mock mode (no API key), a response that couldn't be parsed as
        # JSON even after stripping code fences, or a provider-level
        # error (e.g. Groq's json-mode validation failing on a
        # truncated response) -- any of these falls back to using the
        # raw query directly so the pipeline still runs end to end.
        search_query = state["query"]
        budget = None

    return {"search_query": search_query, "budget": budget}


def retriever_node(state: StyleScoutState) -> dict:
    """Pull grounding context from both MCP tools for the cleaned query."""

    catalog_results = call_tool(
        "catalog_search", {"query": state["search_query"], "top_k": 8}
    )
    trend_results = call_tool(
        "trend_lookup", {"query": state["search_query"], "top_k": 3}
    )

    return {"catalog_results": catalog_results, "trend_results": trend_results}


def _fallback_selection(state: StyleScoutState) -> dict:
    """
    Used when the model's response can't be parsed as JSON. Picks the
    top few retrieved items by relevance so the rest of the pipeline
    -- including the budget_check tool call -- still runs end to end.

    This can happen for two different reasons, and the message shown to
    the user needs to say which one actually occurred:

      1. No API key is configured at all -- call_llm() returns the
         deterministic mock text, which is never valid JSON. This is
         true mock mode.
      2. A real key IS configured and the model actually responded, but
         its response couldn't be parsed as JSON (rare now that the
         Groq call uses json_mode, but kept as a safety net). This is
         NOT mock mode -- mislabeling it that way is misleading, since
         the user's key is working fine elsewhere in the pipeline.
    """

    top_items = state["catalog_results"][:3]

    if has_real_provider():
        styling_notes = (
            "[FALLBACK] A real API key is configured, but the model's last "
            "response couldn't be parsed as structured JSON, so this is a "
            "placeholder pick of the top retrieved items rather than a real "
            "styling rationale. This is usually transient -- try the same "
            "request again."
        )
    else:
        styling_notes = (
            "[MOCK MODE] No GROQ_API_KEY or ANTHROPIC_API_KEY is set, so this "
            "is a placeholder pick of the top retrieved items rather than a "
            "real styling rationale."
        )

    return {
        "selected_item_ids": [item["item_id"] for item in top_items],
        "styling_notes": styling_notes,
    }


def stylist_node(state: StyleScoutState) -> dict:
    """
    Pick a small set of item_ids from the retrieved catalog results and
    write a short plain-prose rationale. The model never writes prices
    or totals itself -- those come from the budget_check tool in the
    critic step, which is the actual source of truth.
    """

    catalog_text = json.dumps(state["catalog_results"], indent=2)
    trend_text = json.dumps(state["trend_results"], indent=2)

    system = (
        "You are a fashion stylist assistant. Choose 2-4 items that "
        "form a complete, coherent outfit using ONLY the item_id values "
        "that appear in CATALOG_RESULTS below -- never invent an "
        "item_id that isn't listed. Respond with ONLY a JSON object: "
        "{\"selected_item_ids\": [list of ints], \"styling_notes\": "
        "\"2-4 sentences of plain prose, no markdown formatting, no "
        "asterisks, explaining why these items work together and how "
        "they tie to the trend notes\"}."
    )

    user = (
        f"User request: {state['query']}\n"
        f"Budget: {state.get('budget')}\n\n"
        f"CATALOG_RESULTS:\n{catalog_text}\n\n"
        f"TREND_RESULTS:\n{trend_text}\n"
    )

    if state.get("critique"):
        user += f"\nA reviewer flagged this issue with your last pick -- fix it: {state['critique']}"

    try:
        # Same reasoning as planner_node: the whole call_llm(...) has to
        # be inside this try, not just the json.loads() after it, since
        # a provider-level error (Groq's json-mode validation rejecting
        # a truncated response) raises from inside the API call itself.
        # max_tokens is bumped from 400 -> 1024 for the same reason: this
        # payload is bigger (styling_notes prose plus the item id list),
        # and a reasoning model's hidden "thinking" tokens eat into the
        # budget before it writes the JSON you actually asked for.
        raw = call_llm(system=system, user=user, max_tokens=1024, json_mode=True)
        parsed = json.loads(strip_json_fences(raw))
        selected_item_ids = [int(i) for i in parsed["selected_item_ids"]]
        styling_notes = parsed["styling_notes"]
    except Exception:
        return _fallback_selection(state)

    return {"selected_item_ids": selected_item_ids, "styling_notes": styling_notes}


def critic_node(state: StyleScoutState) -> dict:
    """
    Self-critic pass, backed by an actual tool call rather than asking
    the LLM to re-check its own arithmetic:

      1. Grounding check: every selected_item_id must be one of the
         item_ids that was actually retrieved (catches hallucinated
         items deterministically, via set membership, not a fuzzy
         text match).
      2. Budget check: the budget_check MCP tool is called with the
         selected ids, which looks up real prices from the catalog and
         sums them -- so "does this fit the budget" is answered by the
         data layer, not by the model's own claim in prose.

    Bounded to one revision loop via revision_count.
    """

    retrieved_ids = {item["item_id"] for item in state["catalog_results"]}
    selected_ids = state.get("selected_item_ids") or []

    issues = []

    ungrounded = [i for i in selected_ids if i not in retrieved_ids]
    if ungrounded or not selected_ids:
        issues.append(
            f"These selected item_ids were not in the retrieved catalog results: {ungrounded or selected_ids}."
        )

    # Only the valid, grounded ids go into the budget_check tool call --
    # no point asking it to price an item_id we already know is bogus.
    valid_ids = [i for i in selected_ids if i in retrieved_ids]
    budget = state.get("budget")

    total_cost = 0.0
    fits_budget = None
    selected_items = []

    if valid_ids:
        budget_result = call_tool(
            "budget_check",
            {"item_ids": valid_ids, "max_budget": budget if budget is not None else 10**9},
        )
        total_cost = budget_result["total_cost"]
        selected_items = budget_result["items"]

        if budget is not None:
            fits_budget = budget_result["fits_budget"]
            if not fits_budget:
                issues.append(
                    f"Selected items total ${total_cost:.2f}, which is over the ${budget} budget by ${-budget_result['difference']:.2f}. Drop an item or swap to a cheaper one."
                )

    revision_count = state.get("revision_count", 0)
    needs_revision = bool(issues) and revision_count < 1

    critique = " ".join(issues) if issues else "No issues found."

    if needs_revision:
        return {
            "critique": critique,
            "needs_revision": True,
            "revision_count": revision_count + 1,
        }

    # Attach full catalog metadata (name, brand, color, etc) to each
    # selected item for the frontend, by joining back against
    # catalog_results rather than trusting budget_check's slimmer shape.
    catalog_by_id = {item["item_id"]: item for item in state["catalog_results"]}
    full_selected_items = [catalog_by_id[i] for i in valid_ids if i in catalog_by_id]

    return {
        "critique": critique,
        "needs_revision": False,
        "selected_items": full_selected_items,
        "total_cost": total_cost,
        "fits_budget": fits_budget,
        "final_output": state["styling_notes"],
    }


def route_after_critic(state: StyleScoutState) -> str:
    """Conditional edge: loop back to the stylist once, or finish."""

    return "stylist" if state.get("needs_revision") else END


# ----------------------------------------------------------------------
# Graph assembly
# ----------------------------------------------------------------------

def build_graph():
    graph = StateGraph(StyleScoutState)

    graph.add_node("planner", planner_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("stylist", stylist_node)
    graph.add_node("critic", critic_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "stylist")
    graph.add_edge("stylist", "critic")
    graph.add_conditional_edges("critic", route_after_critic, {"stylist": "stylist", END: END})

    return graph.compile()


def run_styling_request(query: str) -> StyleScoutState:
    """Convenience entry point used by the API layer and CLI tests."""

    app = build_graph()

    initial_state: StyleScoutState = {
        "query": query,
        "search_query": "",
        "budget": None,
        "catalog_results": [],
        "trend_results": [],
        "selected_item_ids": [],
        "styling_notes": "",
        "critique": "",
        "needs_revision": False,
        "revision_count": 0,
        "selected_items": [],
        "total_cost": 0.0,
        "fits_budget": None,
        "final_output": "",
    }

    return app.invoke(initial_state)


if __name__ == "__main__":
    result = run_styling_request("I need a cozy preppy outfit for fall under $200")
    print("SEARCH QUERY:", result["search_query"])
    print("BUDGET:", result["budget"])
    print()
    print("SELECTED ITEMS:")
    for item in result["selected_items"]:
        print(f"  - {item['name']} (${item['price']})")
    print(f"TOTAL: ${result['total_cost']:.2f}  FITS BUDGET: {result['fits_budget']}")
    print()
    print("STYLING NOTES:")
    print(result["final_output"])
    print()
    print("CRITIQUE:", result["critique"])
