import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import search_listings, suggest_outfit, create_fit_card


# ─────────────────────────────────────────────
# Tool 1: search_listings
# ─────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown xxyyzz", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# ─────────────────────────────────────────────
# Tool 2: suggest_outfit
# ─────────────────────────────────────────────

def test_suggest_outfit_non_empty():
    new_item = {
        "title": "Vintage Tee",
        "price": 20,
        "platform": "depop"
    }

    wardrobe = {
        "items": [
            {"name": "Baggy Jeans", "category": "pants"},
            {"name": "Sneakers", "category": "shoes"}
        ]
    }

    result = suggest_outfit(new_item, wardrobe)

    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_suggest_outfit_empty_wardrobe():
    new_item = {"title": "Tee", "price": 10, "platform": "depop"}

    wardrobe = {"items": []}

    result = suggest_outfit(new_item, wardrobe)

    assert isinstance(result, str)
    assert len(result.strip()) > 0


# ─────────────────────────────────────────────
# Tool 3: create_fit_card
# ─────────────────────────────────────────────

def test_create_fit_card_valid():
    outfit = "Pair with baggy jeans and sneakers."

    new_item = {
        "title": "Vintage Tee",
        "price": 22,
        "platform": "depop"
    }

    result = create_fit_card(outfit, new_item)

    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_create_fit_card_missing_outfit():
    new_item = {
        "title": "Vintage Tee",
        "price": 22,
        "platform": "depop"
    }

    result = create_fit_card("", new_item)

    assert "Missing outfit context. Cannot generate fit card" in result