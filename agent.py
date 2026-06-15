import re
from typing import Dict, Any
from tools import search_listings, suggest_outfit, create_fit_card


def _new_session(query: str, wardrobe: dict):
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ──────────────────────────────────────────────────────────
#  PARSER WITH IMPROVED SIZE DETECTION AND PRICE EXTRACTION
# ──────────────────────────────────────────────────────────
def _parse_query(query: str):

    q = query.lower()

    # --------------------------
    # SIZE FIX (SHOES + CLOTHING)
    # --------------------------

    size = None

    # clothing sizes first
    m1 = re.search(r"\b(xs|s|m|l|xl|xxl)\b", q)

    # shoe / numeric sizes (IMPORTANT FIX: must detect 8, 8.5 correctly)
    m2 = re.search(r"\b(\d+(\.\d+)?)\b", q)

    if m1:
        size = m1.group(1).upper()

    elif m2:
        size = m2.group(1)  # <-- FIXED (was wrong group earlier in many versions)

    # --------------------------
    # PRICE
    # --------------------------

    max_price = None
    price_match = re.search(r"\$(\d+)|under\s*(\d+)|below\s*(\d+)", q)

    if price_match:
        for g in price_match.groups():
            if g:
                max_price = float(g)
                break

    # --------------------------
    # CLEAN DESCRIPTION
    # --------------------------

    cleaned = re.sub(r"\$\d+|under\s*\d+|below\s*\d+", "", q)
    cleaned = re.sub(r"\b(xs|s|m|l|xl|xxl)\b", "", cleaned)
    cleaned = re.sub(r"\b\d+(\.\d+)?\b", "", cleaned)
    cleaned = cleaned.replace("size", "").strip()

    return {
        "description": cleaned,
        "size": size,
        "max_price": max_price,
    }


# ─────────────────────────────────────────────
# AGENT LOOP
# ─────────────────────────────────────────────


def run_agent(query: str, wardrobe: dict):

    session = _new_session(query, wardrobe)

    parsed = _parse_query(query)
    session["parsed"] = parsed

    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )

    session["search_results"] = results

    if not results:
        session["error"] = "NO_RESULTS"
        return session

    selected = results[0]
    session["selected_item"] = selected

    outfit = suggest_outfit(selected, wardrobe)
    session["outfit_suggestion"] = outfit

    session["fit_card"] = create_fit_card(outfit, selected)

    return session


# ─────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")