# FitFindr — planning.md

FitFindr processes a user’s thrift shopping query by extracting search filters (description, size, and price) and querying a structured listings dataset to find the most relevant item. If a match is found, it generates outfit suggestions using the user’s wardrobe and then creates a social-media-ready caption for the selected item. If no listings are found, the system stops early and prompts the user to refine their search.

Each listing in listings.json contains:

id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, and platform.
These fields are used for filtering, ranking, and selecting the best match during search_listings().

The suggest_outfit() tool receives a wardrobe object based on wardrobe_schema.json, which defines the structure of user-owned clothing items.
get_example_wardrobe() is used for realistic testing with populated clothing items
get_empty_wardrobe() is used to test fallback behavior when no wardrobe data exists

When the wardrobe is empty, the agent must return general styling advice instead of failing.

## Tools

### Tool 1: search_listings

**What it does:**

Search the mock listings dataset for items matching the description,
optional size, and optional price ceiling.
Search: search_listings("vintage graphic tee", size="M", max_price=30.0) returns 3 matching listings sorted by relevance. FitFindr picks the top result: "Graphic Tee — 2003 Tour Bootleg Style — $24, depop, good condition."

**Input parameters:**

- `description` (str): Keywords describing what the user is looking for
  (e.g., "vintage graphic tee").
- `size` (str): Size string to filter by, or None to skip size filtering.
  Matching is case-insensitive (e.g., "M" matches "S/M").
- `max_price` (float): Maximum price (inclusive), or None to skip price filtering.

**What it returns:**

A list of matching listing dicts, sorted by relevance (best match first).

Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

**What happens if it fails or returns nothing:**

Returns an empty list if nothing matches — does NOT raise an exception.

If search_listings returns nothing, FitFindr tells the user what to try differently and stops — it does not call suggest_outfit with empty input.

### Tool 2: suggest_outfit

**What it does:**

Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

Suggest outfit: suggest_outfit(new_item=<band tee>, wardrobe=<user's wardrobe>) returns: "Pair the Graphic Tee with the baggy straight-leg jeans and black combat boots. Add the vintage black denim jacket to complete the look. This outfit is perfect for a casual, laid-back day out ---"

**Input parameters:**

- `new_item` (dict): A listing dict (the item the user is considering buying).
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of wardrobe item dicts. May be empty — handle this gracefully.

**What it returns:**

A non-empty string with outfit suggestions.

**What happens if it fails or returns nothing:**

If the wardrobe is empty, offer general styling advice for the item
rather than raising an exception or returning an empty string.

### Tool 3: create_fit_card

**What it does:**

Generate a short, shareable outfit caption for the thrifted find.

Fit card: create_fit_card(outfit=<suggestion>, new_item=<band tee>) returns: "Get ready to rock with my Graphic Tee - 2003 Tour Bootleg Style, now available on Depop for just $24. This vintage-style bootleg tee is perfect for adding a grunge touch to your wardrobe---"

**Input parameters:**

- `outfit` (str): The outfit suggestion string from suggest_outfit().
  new_item: The listing dict for the thrifted item.

**What it returns:**

A 2–4 sentence string usable as an Instagram/TikTok caption.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

**What happens if it fails or returns nothing:**

If outfit is empty or missing, return a descriptive error message
string — do NOT raise an exception.


## Planning Loop

**How does your agent decide which tool to call next?**

The agent decides which tool to call next based on the current state stored in the session and the output of the previous tool.

The agent uses a state-driven sequential pipeline: it always starts with search, then conditionally calls outfit suggestion and fit card generation based on whether valid session state exists.

Step 1 — Parse and initialize state

The agent first parses the user query into structured inputs (description, size, max_price) and stores them in session["parsed"].

Step 2 — Always start with search_listings

The first tool called is always search_listings() because it is the entry point for retrieving candidate items.

The agent decides the next step based on its output:

If the result is empty → it sets session["error"] = "NO_RESULTS" and stops execution immediately
If results exist → it selects the top item and stores it in session["selected_item"]

Step 3 — Conditional progression to outfit generation

If a valid selected_item exists, the agent calls suggest_outfit().

This decision is state-based, meaning the tool is only called if:

A valid listing was found
No error state is active

The output is stored in session["outfit_suggestion"].

Step 4 — Final tool execution (fit card generation)

If an outfit suggestion exists, the agent calls create_fit_card().

This step is also conditional and depends on:

selected_item being valid
outfit_suggestion being present

The output is stored in session["fit_card"].

Step 5 — Termination condition

The agent stops when:

A failure occurs (empty search results), OR
The final fit_card is generated successfully

## State Management ##

The agent uses a single session dictionary (session) as the source of truth for all intermediate and final outputs. Each tool reads only the inputs it needs and writes its output back into the session, ensuring a linear and traceable flow of data across the planning loop.

Each tool is stateless, meaning it does not store memory internally. Instead, it reads required inputs from the session and writes its output back into it.

**How state is structured**

The session is updated step-by-step as the pipeline executes:

session["parsed"]: Stores parsed user query (description, size, max_price)
session["search_results"]: Stores raw output from search_listings()
session["selected_item"]: Stores the top-ranked listing selected from results
session["outfit_suggestion"]: Stores output from suggest_outfit()
session["fit_card"]: Stores final generated caption from create_fit_card()
session["error"]: stores error states like "NO_RESULTS"

**How state flows**

User query is parsed and stored in session
search_listings() writes results into session
Top result is saved as selected_item
suggest_outfit() uses selected_item + wardrobe and stores output
create_fit_card() uses both outputs and stores final result

Each step depends only on session state, not direct function chaining.

**How does information from one tool get passed to the next?**

The agent uses a single session dictionary as the source of truth for each interaction. The query parser writes `description`, `size`, and `max_price` into `session["parsed"]`; `search_listings()` writes its matched list to `session["search_results"]`; the top match is saved to `session["selected_item"]`; then `suggest_outfit()` and `create_fit_card()` write `session["outfit_suggestion"]` and `session["fit_card"]`, respectively. If an error occurs or no search results are found, `session["error"]` is set and the loop returns early.

## Error Handling

**search_listings**

* **Failure Mode:** No results match the query filters (description, size, max_price)
* **Agent Response:** The agent stops execution and returns: *"No matching listings found. Try broader keywords or increase budget."* It does not call downstream tools and sets `session["error"] = "NO_RESULTS"`.

**suggest_outfit**

* **Failure Mode:** Wardrobe is empty
* **Agent Response:** The tool returns general styling advice based on the selected item (e.g., denim pairings, sneakers, layering ideas). It always returns a non-empty string and never fails.

**create_fit_card**

* **Failure Mode:** Outfit input is missing or incomplete
* **Agent Response:** The tool returns a safe fallback caption: *"Missing outfit context. Cannot generate fit card"* It always returns a valid string and never crashes.

**system-level execution**

* **Failure Mode:** Invalid pipeline state (missing `selected_item` or skipped step)
* **Agent Response:** The planning loop stops execution and prevents downstream tool calls. It ensures no tool runs with incomplete session state.
state.                         

All tools are expected to fail gracefully and never crash the pipeline. The planning loop is responsible for stopping execution immediately when a required dependency is missing.

## Architecture


User query
    │
    ▼
Planning Loop ───────────────────────────────────────────┐
    │                                                    │
    ├─► search_listings(description, size, max_price)    │
    │       │ results=[]                                 │
    │       ├──► [ERROR] "No listings found..." → return │
    │       │                                            │
    │       │ results=[item, ...]                        │
    │       ▼                                            │
    │   Session: selected_item = results[0]              │
    │       │                                            │
    ├─► suggest_outfit(selected_item, wardrobe)          │
    │       │                                            │
    │   Session: outfit_suggestion = "..."               │
    │       │                                            │
    └─► create_fit_card(outfit_suggestion, selected_item)│
            │                                            │
        Session: fit_card = "..."                        │
            │                                            └─ error path returns here
            ▼
        Return session


        


                         ┌────────────────────────────┐
                         │            USER            │
                         │  "vintage tee under $30"   │
                         └────────────┬───────────────┘
                                      │
                                      ▼
                         ┌────────────────────────────┐
                         │       PLANNING LOOP        │
                         │  (controls execution flow) │
                         └────────────┬───────────────┘
                                      │
                                      ▼
                    ┌────────────────────────────────────┐
                    │ Parse Query                        │
                    │ description, size, max_price       │
                    │                                    │
                    │ Session:                           │
                    │ session["parsed"]                  │
                    └────────────┬───────────────────────┘
                                 │
                                 ▼
        ┌──────────────────────────────────────────────────────────┐
        │ Tool: search_listings                                    │
        │ Input: parsed fields                                     │
        │                                                          │
        │ Session Update:                                          │
        │ session["search_results"]                                │
        └────────────┬─────────────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
┌───────────────────┐   ┌────────────────────────────┐
│ results = []      │   │ results = [item1, item2...]│
│                   │   │                            │
│ Session:          │   │ Session:                   │
│ session["error"]  │   │ session["selected_item"]   │
│ = "No matching    |   |                            |
|listings found""   │   │ = results[0]               │
└─────────┬─────────┘   └────────────┬──────────────┘
          │                          │
          ▼                          ▼
     EARLY RETURN            ┌──────────────────────────────┐
                             │ Tool: suggest_outfit         │
                             │ Input: selected_item,        │
                             │        wardrobe              │
                             │                              │
                             │ Session Update:              │
                             │ session["outfit_suggestion"] │
                             └────────────┬─────────────────┘
                                          │
                                          ▼
                             ┌──────────────────────────────┐
                             │ Tool: create_fit_card        │
                             │ Input: outfit_suggestion,    │
                             │        selected_item         │
                             │                              │
                             │ Session Update:              │
                             │ session["fit_card"]          │
                             └────────────┬─────────────────┘
                                          │
                                          ▼
                             ┌──────────────────────────────┐
                             │        FINAL OUTPUT          │
                             │  Return full session:        │
                             │  - selected_item             │
                             │  - outfit_suggestion         │
                             │  - fit_card                  │
                             └──────────────────────────────┘

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I will use ChatGPT to implement each tool based strictly on its specification in planning.md.

**search_listings**

I will provide:

Tool 1 spec (inputs, return type, failure mode)
listings schema from data/listings.json
load_listings() from utils/data_loader.py

Expected output:

Function that filters by description, size, and max_price
Returns ranked list sorted by relevance
Returns empty list for no matches

Verification:

Test with valid query, size filter, and price filter
Test edge case: no matches
Confirm correct field usage (no missing filters)

**suggest_outfit**

I will provide:

Tool 2 spec
wardrobe schema from wardrobe_schema.json
example + empty wardrobe cases

Expected output:

1–2 outfit suggestions based on selected item
Graceful fallback when wardrobe is empty
Always returns non-empty string

Verification:

Test with populated wardrobe
Test with empty wardrobe
Ensure no exceptions or null returns

**create_fit_card**

I will provide:

Tool 3 spec
outfit output format examples
listing metadata structure

Expected output:

2–4 sentence casual social caption
Includes item name, price, platform
Always returns valid string

Verification:

Test with valid outfit input
Test with missing/incomplete input
Ensure safe fallback behavior

**Milestone 4 — Planning loop and state management:**

I will use ChatGPT to implement the planning loop using the full system design context.

Inputs provided:
Planning Loop section from planning.md
State Management section (session structure)
Agent architecture diagram

Expected behavior:

The planning loop will:

Parse user query → extract description, size, max_price
Call search_listings()
If empty results → set session["error"] and stop execution
Store top result in session["selected_item"]
Call suggest_outfit()
Store output in session["outfit_suggestion"]
Call create_fit_card()
Store final output in session["fit_card"]
Return final session response

Verification:

I will ensure:

Correct sequential execution of tools
No tool runs without required inputs
Session state is updated after every step
Early exit works for empty search results
No partial execution occurs after failure
Final output matches expected user experience flow

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1: Query parsing + search**
The agent parses the user input and extracts:

description: "vintage graphic tee"
max_price: 30
size: None or M (if provided)

It then calls:

search_listings(description="vintage graphic tee", size="M", max_price=30.0)

Tool output:
Returns a ranked list of matching listings
The agent selects the top result:

selected_item = "Graphic Tee — 2003 Tour Bootleg Style — $24, depop"

**Step 2: Outfit generation**
The agent checks that selected_item exists and no error state is set.

It then calls:

suggest_outfit(new_item=selected_item, wardrobe=session["wardrobe"])

Tool output:
Returns outfit suggestion such as:

“Pair the graphic tee with the baggy straight-leg jeans and black combat boots. Add the vintage black denim jacket to give the outfit a cool, edgy vibe. Finish with the brown leather belt and black crossbody bag for a chic touch.”

The agent stores:
session["outfit_suggestion"]

**Step 3: Fit card generation**
The agent verifies that both:

selected_item
outfit_suggestion

exist in session.

It then calls:

create_fit_card(outfit=session["outfit_suggestion"], new_item=selected_item)

**Final output to user:**

Returns a social caption like:

“Get ready to rock with my Graphic Tee - 2003 Tour Bootleg Style ($24) available on Depop. This vintage-inspired tee is a must-have for any grunge or streetwear fan. I've created four epic outfits to showcase its versatility: Grunge Revival, Streetwear Chic, Layered Look, and Summer Vibes. Which one is your fave? Head to my Depop shop (link in bio) to cop this awesome tee and create your own unique looks #GraphicTee #VintageVibes #GrungeFashion #Streetwear #DepopFind 🖤”

The agent stores:
session["fit_card"]

**Real output in UI for the example query above**

The Gradio UI displays output using a function called handle_query() which returns a 3-element tuple. Each element maps directly to one UI panel: the first shows the selected listing, the second shows outfit suggestions, and the third shows the generated fit card.

Internally, handle_query() calls run_agent() which executes the full tool pipeline and stores results in a session object. After execution, the session values are formatted and returned as strings. If an error occurs, only the first panel shows an error message while the other two remain empty.

The system returns a structured response containing:

**Selected listing:**

Graphic Tee — 2003 Tour Bootleg Style
💰 Price: $24.0

📏 Size: L

🏷️ Brand: None

📦 Platform: depop

✨ Condition: good

Vintage-style bootleg tee with faded graphic. Slightly boxy fit. 100% cotton, soft and worn-in.

**Outfit idea:**

I love working with this item. Here are some outfit suggestions for the Graphic Tee — 2003 Tour Bootleg Style:

Outfit 1: Grunge Revival
Pair the graphic tee with the baggy straight-leg jeans and black combat boots. Add the vintage black denim jacket to give the outfit a cool, edgy vibe. Finish with the brown leather belt and black crossbody bag for a chic touch.

Outfit 2: Streetwear Chic
Combine the graphic tee with the wide-leg khaki trousers and chunky white sneakers. This outfit is perfect for a casual, streetwear-inspired look. You can add the black cropped zip hoodie for a layered effect, or wear it on its own for a more relaxed vibe.

Outfit 3: Layered Look
Layer the graphic tee under the oversized grey crewneck sweatshirt. Pair with the baggy straight-leg jeans and black combat boots for a cozy, laid-back outfit. Add the black crossbody bag to complete the look.

Outfit 4: Summer Vibes
Wear the graphic tee with the white ribbed tank top underneath (optional) and the wide-leg khaki trousers. Slip on the chunky white sneakers and add the brown leather belt for a relaxed, summery feel. You can also add the vintage black denim jacket for a cooler evening look.

These outfits showcase the graphic tee's versatility and how it can be styled in different ways to create unique looks. Feel free to experiment and add your own personal touches to make the outfits your own!

**Your fit card**

Get ready to rock with my Graphic Tee - 2003 Tour Bootleg Style ($24) available on Depop. This vintage-inspired tee is a must-have for any grunge or streetwear fan. I've created four epic outfits to showcase its versatility: Grunge Revival, Streetwear Chic, Layered Look, and Summer Vibes. Which one is your fave? Head to my Depop shop (link in bio) to cop this awesome tee and create your own unique looks #GraphicTee #VintageVibes #GrungeFashion #Streetwear #DepopFind

**Error path**

If search_listings() returns an empty list:

The agent stops immediately sets session["error"] = "NO_RESULTS"

Returns a message like:

“No matching items found. Try broader keywords or increase your price range.”

No further tools are called.

