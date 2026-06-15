# FitFindr — AI Planning Agent

## Overview

FitFindr is an AI-powered fashion assistant that helps users:
search for clothing items based on natural language queries
generate outfit suggestions
create styled “fit cards” (social-ready captions)

It uses a multi-step agent workflow combined with structured tools and an LLM to simulate a personalized styling experience.

It uses a **planning loop architecture**, where the agent makes decisions step-by-step instead of executing a fixed pipeline.

The agent:

- Parses natural language queries
- Searches a mock listings dataset
- Selects the best matching item
- Generates outfit suggestions using wardrobe context
- Creates a social media “fit card” caption

## Tool Inventory

### 1. search_listings

**Inputs:**

- description (str): keywords from user query
- size (str | None): optional size filter
- max_price (float | None): optional price limit

**Outputs:**

- list[dict]: ranked listing results (empty list if no matches)

**Purpose:**
Searches a mock secondhand marketplace and returns relevant clothing items ranked by keyword relevance and filtered by constraints.

### 2. suggest_outfit

**Inputs:**

- new_item (dict): selected listing
- wardrobe (dict): user wardrobe with "items" list

**Outputs:**

- str: AI-generated outfit suggestion

**Purpose:**
Generates outfit combinations using the selected item and wardrobe context (or fallback styling advice if wardrobe is empty).

### 3. create_fit_card

**Inputs:**

- outfit (str)
- new_item (dict)

**Outputs:**

- str: Instagram/TikTok-style caption

**Purpose:**
Transforms outfit suggestions into a natural, social-media-ready caption.

## Planning Loop (Decision Logic)

The agent does NOT execute tools blindly. It follows a conditional decision flow:

1. Parse user query into:
   - description
   - size
   - max_price

2. Call search_listings()

3. Decision point:
   - If results == []:
     → set session["error"]
     → STOP execution (do NOT call other tools)
   - Else:
     → continue pipeline

4. Select top result → session["selected_item"]

5. Call suggest_outfit() using selected_item + wardrobe

6. Call create_fit_card() using outfit + selected_item

7. Return session

 Key behavior: the pipeline branches based on search_listings output.

## State Management

All tool outputs are stored in a single session dictionary:

- parsed → extracted query parameters
- search_results → raw listings from search tool
- selected_item → top-ranked listing
- outfit_suggestion → LLM-generated outfit text
- fit_card → final caption output
- error → early termination message

### Flow:

Each tool reads from and writes to session state.

This ensures:

- reproducibility
- traceable debugging
- no hidden dependencies between tools

##  Error Handling Strategy

| Tool            | Failure Mode        | Behavior                                   |
| --------------- | ------------------- | ------------------------------------------ |
| search_listings | No matches          | Returns [], agent stops with error message |
| suggest_outfit  | Empty wardrobe      | Returns general styling advice (no crash)  |
| create_fit_card | Empty outfit string | Returns error message instead of crashing  |

### Concrete Test Evidence (from CLI testing)

search_listings("designer ballgown", size="XXS", max_price=5)

→ Output:
[]

suggest_outfit(result[0], get_empty_wardrobe())

→ Output:
""Try pairing this piece with neutral staples like denim or layered basics to balance the silhouette...""

create_fit_card("", result[0])

→ Output:
"Missing outfit context. Cannot generate fit card"

## Spec Reflection

### How the spec helped:

The project specification provided a clear multi-tool architecture (search_listings → suggest_outfit → create_fit_card) which helped structure the system into a predictable planning loop.
It also defined strict responsibilities for each tool, which made debugging easier because each stage could be tested independently instead of debugging the full pipeline at once.

### How implementation diverged (and why):

One key divergence was in the query parsing and size handling logic inside agent.py and tools.py.

The original spec implied simple string-based filtering for size and description.
In practice, this was insufficient because:
shoe sizes (e.g., 8, 8.5) were incorrectly matched with nearby values like 7 or 8.5
clothing sizes (S, M, L) and numeric sizes needed different handling

**What was changed**

To fix this, the implementation introduced:

numeric extraction using regex
strict equality matching for shoe sizes
separate handling for letter-based clothing sizes vs numeric shoe sizes

**Why this divergence was necessary :**

The dataset contained mixed size formats, so a naive substring match caused incorrect recommendations. The improved logic ensured accurate filtering across all categories (tops, bottoms, shoes, accessories), which the original simplified spec did not fully account for.

## AI Usage

This project used AI as a development assistant to design logic, debug issues, and improve system behavior. Below are specific examples of how AI suggestions were applied and later modified.

### Instance 1 — Scoring System for Listing Relevance in search_listings()

AI initially suggested a simple keyword overlap approach to rank listings based on user queries. This produced unstable results where irrelevant items could rank higher due to random word matches.

I revised the implementation by introducing a weighted scoring system:

Higher weight for category matches (e.g., “shoes”, “tops”)
Medium weight for style tags (e.g., “vintage”, “streetwear”)
Lower weight for general text overlap

This override improved ranking accuracy and ensured more relevant listings appear at the top of results.

### Instance 2 — Size Matching Fix

AI asked the AI to fix inconsistent size matching where:

shoe size “8” was incorrectly matching “7” 
clothing sizes (S, M, L) were mixed with numeric sizes

The final solution I implemented:

separates numeric vs letter sizes
uses strict equality for numeric sizes
ensures correct filtering across all categories (shoes, tops, bottoms, etc.)

## Demo Instructions

Run the application:

pip install -r requirements.txt
python app.py

Open the Gradio UI link:
http://127.0.0.1:7860

### Happy Path Example:

Input:
"vintage graphic tee under $30"

Output:

- Listing result displayed
- Outfit suggestion generated
- Fit card caption created

### Failure Path Example:

Input:
"designer ballgown under $5"

Output:

- Error message shown in first panel
- Other panels remain empty
- No downstream tool execution occurs


**How to Run test**

 python -m pip install pytest
 python -m pytest  



## Enhancement Roadmap (Future Work)

This project is designed with modular tools and a session-based architecture, making it easy to extend in future iterations. The following enhancements are planned:

### 1. Price Comparison Intelligence

Future versions could analyze similar listings in the dataset to:

Compare price ranges within the same category (e.g., shoes vs shoes)
Highlight “good deal” vs “above average price”
Provide reasoning based on dataset statistics rather than only filtering

### 2. Style Profile Memory

A persistent user profile system could be added to:

Store preferred styles (e.g., vintage, streetwear, minimal)
Remember frequently selected categories and sizes
Personalize outfit suggestions across multiple sessions

Implementation idea:

Save user preferences in a lightweight JSON or database layer
Load preferences at the start of each session

### 3. Trend Awareness Layer

Outfit suggestions could be enhanced using trend signals such as:

Seasonal fashion trends (e.g., Y2K revival, oversized silhouettes)
External APIs or curated trend datasets
Trend-weighted scoring in search_listings()

### 4. Smart Retry & Relaxation Logic

Currently, the system stops when no results are found. A future improvement could:

Automatically retry search with relaxed constraints
Gradually remove filters (price → size → keyword strictness)
Clearly inform the user what was adjusted

Example behavior:

“No exact matches found. Showing similar items without size restriction.”

### 5. Improved Ranking Model

Replace rule-based scoring with:

TF-IDF or embedding-based similarity
Semantic matching for better understanding of fashion descriptions
Better handling of synonyms (e.g., “boots” vs “ankle boots”)

## Design Philosophy

All enhancements are designed to preserve the current system’s strengths:

modular tool structure
session-based flow
simple, testable components
easy integration with LLM-based reasoning|