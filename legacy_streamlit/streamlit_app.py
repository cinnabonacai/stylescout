"""
streamlit_app.py

StyleScout demo UI.

Matches the pattern of the other deployed Streamlit projects (hip-hop
recommender, finance chatbot): a simple single-page app, no auth, free
text input in, agent output rendered below along with the retrieved
context so a viewer can see the RAG grounding, not just the final
answer.

Run locally with:
    streamlit run app/streamlit_app.py

Requires ANTHROPIC_API_KEY to be set in the environment for real model
output (see README.md).
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# So `agent` and `tools` are importable when Streamlit runs this file
# directly rather than as part of a package.
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
from agent.graph import run_styling_request


st.set_page_config(page_title="StyleScout", page_icon="👗", layout="centered")

st.title("👗 StyleScout")
st.caption(
    "An agentic styling assistant: tell it an occasion, vibe, or budget, "
    "and it searches a product catalog + fall/winter 2026 trend notes to "
    "put together a grounded outfit recommendation."
)

if not (os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
    st.warning(
        "No GROQ_API_KEY or ANTHROPIC_API_KEY found in the environment -- "
        "running in mock mode. Get a free key at console.groq.com and set "
        "it as GROQ_API_KEY to see real styling recommendations.",
        icon="⚠️",
    )

query = st.text_input(
    "What are you dressing for?",
    placeholder="e.g. a cozy preppy outfit for fall under $150",
)

run = st.button("Style me", type="primary")

if run and query.strip():
    with st.spinner("Planning, searching the catalog, and styling..."):
        result = run_styling_request(query)

    st.subheader("Recommendation")
    st.write(result["final_output"])

    with st.expander("How the agent got there"):
        st.markdown(f"**Search query used:** {result['search_query']}")
        if result.get("budget"):
            st.markdown(f"**Budget detected:** ${result['budget']}")

        st.markdown("**Retrieved catalog items:**")
        for item in result["catalog_results"]:
            st.markdown(
                f"- {item['name']} ({item['color']}, {item['style_tags']}) "
                f"-- ${item['price']:.2f} [{item['brand']}] "
                f"-- relevance {item['relevance']}"
            )

        st.markdown("**Retrieved trend notes:**")
        for t in result["trend_results"]:
            st.markdown(f"- `{t['trend_id']}` -- relevance {t['relevance']}")

        st.markdown(f"**Self-critique:** {result['critique']}")

elif run:
    st.info("Type a request above first.")
