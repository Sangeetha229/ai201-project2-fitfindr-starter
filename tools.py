import os
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()


# ─────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────


def _get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Missing GROQ_API_KEY")
    return Groq(api_key=api_key)


# ─────────────────────────────────────────────
# SIZE HANDLING
# ─────────────────────────────────────────────


def _extract_number(size: str):
    if not size:
        return None
    m = re.search(r"(\d+(\.\d+)?)", str(size))
    return float(m.group(1)) if m else None


def _extract_letter(size: str):
    if not size:
        return None
    m = re.search(r"\b(xs|s|m|l|xl|xxl)\b", str(size).lower())
    return m.group(1).upper() if m else None


def _size_match(query_size: str | None, item_size: str) -> bool:
    """
    STRICT RULE:
    - numeric sizes MUST match exactly (8 ≠ 7)
    - letter sizes allow loose matching (M matches S/M)
    """

    if not query_size:
        return True

    q_num = _extract_number(query_size)
    i_num = _extract_number(item_size)

    q_letter = _extract_letter(query_size)
    i_letter = _extract_letter(item_size)

    # STRICT numeric match (FIX FOR SHOES BUG)
    if q_num is not None and i_num is not None:
        return q_num == i_num

    # letter match
    if q_letter and i_letter:
        return q_letter in i_letter or i_letter in q_letter

    return query_size.lower() in item_size.lower()



# ─────────────────────────────────────────────
# CATEGORY DETECTION 
# ─────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "tops": ["tee", "shirt", "hoodie", "sweater", "tank", "top", "crewneck"],
    "bottoms": ["pants", "jeans", "cargo", "trousers", "shorts"],
    "shoes": ["boots", "sneakers", "shoes", "heels", "loafers"],
    "outerwear": ["jacket", "coat", "blazer", "windbreaker"],
    "accessories": ["bag", "belt", "hat", "cap"],
}


def _detect_category(query: str) -> str | None:
    q = query.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in q for k in kws):
            return cat
    return None


def _score(item: dict, query: str) -> int:
    """
    Strong deterministic scoring.
    Category mismatch = heavy penalty prevention via filter (not score).
    """

    q = query.lower()
    score = 0

    text = (
        item.get("title", "").lower()
        + " "
        + item.get("description", "").lower()
        + " "
        + " ".join(item.get("style_tags", [])).lower()
    )

    for word in q.split():
        if word in text:
            score += 2

    return score


# ────────────────────────────────────────────
# TOOL 1: SEARCH LISTINGS 
# ─────────────────────────────────────────────


def search_listings(description: str, size=None, max_price=None):

    listings = load_listings()
    results = []

    # print("\n[DEBUG] QUERY:", description, size, max_price)

    def extract_num(s):
        import re

        m = re.search(r"(\d+(\.\d+)?)", str(s or ""))
        return float(m.group(1)) if m else None

    expected_category = None
    q = (description or "").lower()

    if any(k in q for k in ["boot", "shoe", "sneaker", "heel"]):
        expected_category = "shoes"
    elif any(k in q for k in ["tee", "shirt", "hoodie", "top"]):
        expected_category = "tops"
    elif any(k in q for k in ["jeans", "pants", "cargo"]):
        expected_category = "bottoms"

    for item in listings:

        item_size = item.get("size", "")

        q_num = extract_num(size)
        i_num = extract_num(item_size)

        # ───────── SIZE CHECK (HARD STOP) ─────────
        if q_num is not None and i_num is not None:
            if q_num != i_num:
                # print("[REJECT SIZE]", item["title"], item_size)
                continue

        # ───────── CATEGORY CHECK (HARD STOP) ─────────
        if expected_category and item.get("category") != expected_category:
            continue

        # ───────── PRICE FILTER ─────────
        if max_price is not None and item.get("price", 0) > max_price:
            continue

        # ───────── SCORE ─────────
        score = 0
        text = (item.get("title", "") + item.get("description", "")).lower()

        for w in q.split():
            if w in text:
                score += 2

        if score > 0:
            results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in results]


# ─────────────────────────────────────────────
# TOOL 2: OUTFIT SUGGESTION
# ─────────────────────────────────────────────


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:

    client = _get_groq_client()
    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        prompt = f"""
You are a stylist.

Item:
{new_item}

User has EMPTY wardrobe.

Give styling ideas + outfit vibe.
"""
    else:
        wardrobe_text = "\n".join(
            f"- {i.get('name')} ({i.get('category')})" for i in wardrobe_items
        )

        prompt = f"""
You are a stylist.

Item:
{new_item}

Wardrobe:
{wardrobe_text}

Suggest outfits.
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return res.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# TOOL 3: FIT CARD
# ─────────────────────────────────────────────


def create_fit_card(outfit: str, new_item: dict) -> str:

    client = _get_groq_client()

    if not outfit:
        return "Missing outfit context. Cannot generate fit card"

    prompt = f"""
Write IG caption.

Item: {new_item}
Outfit: {outfit}

Must mention:
- name
- price
- platform
"""

    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )

    return res.choices[0].message.content.strip()
