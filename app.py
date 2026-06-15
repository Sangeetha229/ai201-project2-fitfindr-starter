"""
app.py

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr

from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# ── query handler ─────────────────────────────────────────────────────────────


def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Handle user query and return UI outputs.

    Args:
        user_query: Text entered by user.
        wardrobe_choice: Selected wardrobe type.

    Returns:
        (listing_text, outfit_suggestion, fit_card)
    """

    # 1. Validate input
    if not user_query or not user_query.strip():
        return "Please enter a valid search query.", "", ""

    # 2. Select wardrobe
    if wardrobe_choice == "Example wardrobe":
        wardrobe = get_example_wardrobe()
    else:
        wardrobe = get_empty_wardrobe()

    # 3. Call agent
    session = run_agent(user_query, wardrobe)

    # 4. Handle errors
    if session.get("error"):
        error_msg = session.get("error")

        if error_msg == "NO_RESULTS":
            return (
                "No matching items found. Try broader keywords, higher price, or removing filters.",
                "",
                "",
            )

        # return (f"Error: {error_msg}", "", "")
        return (error_msg, "", "")

    # 5. Format output
    selected_item = session.get("selected_item", {})

    listing_text = (
        f"🛍️ {selected_item.get('title', 'Unknown Item')}\n"
        f"💰 Price: ${selected_item.get('price', 'N/A')}\n"
        f"📏 Size: {selected_item.get('size', 'N/A')}\n"
        f"🏷️ Brand: {selected_item.get('brand', 'N/A')}\n"
        f"📦 Platform: {selected_item.get('platform', 'N/A')}\n"
        f"✨ Condition: {selected_item.get('condition', 'N/A')}\n\n"
        f"{selected_item.get('description', '')}"
    )

    outfit_suggestion = session.get(
        "outfit_suggestion", "No outfit suggestion available."
    )

    fit_card = session.get("fit_card", "No fit card available.")

    return listing_text, outfit_suggestion, fit_card


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",
]


def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
""")

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )

            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )

            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )

            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
