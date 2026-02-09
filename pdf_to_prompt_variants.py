# pdf_to_prompt_variants.py

def generate_extraction_prompt_for_pdf(pdf_path=None):
    return (
        "You are extracting product VARIANTS from a technical PDF.\n"
        "You will receive two placeholders:\n"
        "- {text}: full raw text of the PDF\n"
        "- {tables}: JSON array of extracted tables (most important)\n\n"
        "RULES:\n"
        "- Prefer TABLES over prose.\n"
        "- Extract ALL variants (usually one row per DN).\n"
        "- Output ONLY JSON (no markdown).\n"
        "- Output MUST be a JSON ARRAY of objects.\n"
        "- Missing values must be 'N/A'.\n"
        "- Keep values as strings.\n\n"
        "CRITICAL:\n"
        "- DN values must be VALUES, never field names.\n"
        "- Always create one JSON object per DN variant.\n"
        "- If any table contains DN / Nennweite / Nominal diameter, you MUST fill 'DN'.\n\n"
        "PDF TEXT:\n"
        "{text}\n\n"
        "PDF TABLES (JSON):\n"
        "{tables}\n"
    )


def generate_format_prompt_for_variants():
    return (
        "You are a strict data normalizer. You receive JSON extracted from a PDF (Stage 1).\n"
        "Normalize it into ONE JSON ARRAY for CSV export.\n\n"
        "INPUT (Stage 1 JSON):\n"
        "{extraction_json}\n\n"
        "OUTPUT:\n"
        "- Return ONLY a JSON array (no markdown, no comments).\n"
        "- Each array element represents one product variant.\n"
        "- Keep keys consistent across all variants.\n"
        "- CANONICAL VARIANT KEY MUST BE 'DN'.\n"
        "- If Stage 1 used 'Nennweite' or 'Nominal size', map it to 'DN'.\n"
        "- Use existing field names when possible.\n"
        "- Use 'N/A' if missing.\n"
        "- Keep values as strings.\n"
    )
