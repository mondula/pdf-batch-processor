import base64
import json
import re
from io import BytesIO
from typing import Any, Dict, List

import openai
from pdf2image import convert_from_path
from PIL import Image

from extract import extract_pdf_content
from config import OPENAI_API_KEY

# ===== Model =====
try:
    from config import OPENAI_MODEL
except Exception:
    # Safe fallback if config import fails
    OPENAI_MODEL = "gpt-5.2"

print("Using OpenAI model:", OPENAI_MODEL)

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ==============================
# OpenAI Responses API helpers
# ==============================

def _responses_text(prompt: str) -> str:
    """Calls the latest OpenAI *Responses* API and returns plain text output."""
    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
        temperature=0,
    )
    return (getattr(resp, "output_text", None) or "").strip()

def _responses_vision(prompt: str, image_url: str) -> str:
    resp = client.responses.create(
        model=OPENAI_MODEL,
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": image_url},
            ],
        }],
        temperature=0,
    )
    return (getattr(resp, "output_text", None) or "").strip()

# ==============================
# Utility helpers
# ==============================

def _strip_code_fences(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()

def _extract_json_substring(s: str) -> str:
    s = _strip_code_fences(s)
    starts = [i for i in (s.find("["), s.find("{")) if i != -1]
    return s[min(starts):].strip() if starts else s

def _cell_str(x) -> str:
    return "" if x is None else str(x).strip()

# ==============================
# Table filter
# ==============================

def is_meaningful_table(table) -> bool:
    if not isinstance(table, list) or len(table) < 2:
        return False
    header = table[0]
    if not isinstance(header, list):
        return False

    header_cells = [_cell_str(c) for c in header]
    non_empty = [c for c in header_cells if c]
    if len(non_empty) < 2:
        return False

    joined = " ".join(c.lower() for c in non_empty)
    keywords = [
        "dn", "nennweite", "nominal", "pressure", "bar",
        "d", "d1", "d2", "d4", "k", "l", "h", "kg", "gewicht",
        "gewinde", "anschluss"
    ]
    return any(k in joined for k in keywords)

# ==============================
# Drawing fallback
# ==============================

def render_pdf_page_to_data_url(pdf_path: str) -> str:
    images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
    buf = BytesIO()
    images[0].save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

DRAWING_VISION_PROMPT = """
Extract drawing metadata and dimension symbols from this technical drawing.
Return JSON only.
""".strip()

def extract_drawing_with_vision(pdf_path: str) -> Dict[str, Any]:
    img_url = render_pdf_page_to_data_url(pdf_path)

    raw = _responses_vision(DRAWING_VISION_PROMPT, img_url)
    try:
        return json.loads(_extract_json_substring(raw))
    except Exception:
        return {"doc_type": "drawing", "error": "vision_parse_failed"}

# ==============================
# Fallback table parsing
# ==============================

def fallback_extract_variants_from_tables(tables) -> List[Dict[str, Any]]:
    for table in tables:
        if len(table) < 2:
            continue
        header = table[0]
        rows = []

        for r in table[1:]:
            row_obj = {}
            for i, h in enumerate(header):
                if h:
                    row_obj[str(h).strip()] = str(r[i]).strip() if i < len(r) and r[i] else "N/A"
            if row_obj:
                rows.append(row_obj)

        if rows:
            return rows

    return []

# ==============================
# Key normalization + DN fix
# ==============================

def normalize_variant_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    def clean_key(k: str) -> str:
        return " ".join(str(k).replace("\n", " ").replace("\r", " ").split())

    out = {}
    for k, v in row.items():
        ck = clean_key(k)
        if ck:
            out[ck] = v

    # Fill DN
    if not out.get("DN"):
        for k, v in out.items():
            kl = k.lower()
            if "dn" == kl or "nennweite" in kl or "nominal" in kl:
                out["DN"] = v
                break

    return out

# ==============================
# Expand numeric DN columns
# ==============================

_NUMERIC_KEY_RE = re.compile(r"^\d+$")

def expand_numeric_dn_columns(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []

    for r in rows:
        numeric_keys = [k for k in r.keys() if _NUMERIC_KEY_RE.match(str(k))]
        if not numeric_keys:
            out.append(r)
            continue

        shared = {k: v for k, v in r.items() if k not in numeric_keys}

        for dk in sorted(numeric_keys, key=int):
            v = r.get(dk)
            if not v or v == "N/A":
                continue

            nr = dict(shared)
            nr["DN"] = dk

            if "Gewinde" not in nr:
                nr["Gewinde"] = v

            out.append(nr)

    return out

# ==============================
# Main pipelines
# ==============================

def process_with_gpt(pdf_path: str, custom_prompt: str) -> List[Dict[str, Any]]:
    data = extract_pdf_content(pdf_path)
    text = data.get("text", "")
    tables_raw = data.get("tables", [])
    tables = [t for t in tables_raw if is_meaningful_table(t)]

    if not tables:
        return [extract_drawing_with_vision(pdf_path)]

    tables_json = json.dumps(tables, ensure_ascii=False)
    prompt = custom_prompt.replace("{text}", text).replace("{tables}", tables_json)

    raw = _responses_text(prompt)
    parsed = json.loads(_extract_json_substring(raw))

    if isinstance(parsed, dict) and "variants" in parsed:
        parsed = parsed["variants"]

    if isinstance(parsed, list):
        normed = [normalize_variant_keys(r) for r in parsed if isinstance(r, dict)]
        return expand_numeric_dn_columns(normed)

    return []

def process_with_gpt_two_calls(pdf_path: str, custom_prompt: str, format_prompt: str) -> List[Dict[str, Any]]:
    data = extract_pdf_content(pdf_path)
    text = data.get("text", "")
    tables_raw = data.get("tables", [])
    tables = [t for t in tables_raw if is_meaningful_table(t)]

    if not tables:
        return [extract_drawing_with_vision(pdf_path)]

    tables_json = json.dumps(tables, ensure_ascii=False)

    # -------- Stage 1 --------
    prompt1 = custom_prompt.replace("{text}", text).replace("{tables}", tables_json)

    raw1 = _responses_text(prompt1)
    parsed1 = json.loads(_extract_json_substring(raw1))

    if isinstance(parsed1, dict) and "variants" in parsed1:
        parsed1 = parsed1["variants"]

    stage1 = [normalize_variant_keys(r) for r in parsed1 if isinstance(r, dict)]
    stage1 = expand_numeric_dn_columns(stage1)

    if not stage1:
        fb = fallback_extract_variants_from_tables(tables)
        stage1 = expand_numeric_dn_columns([normalize_variant_keys(r) for r in fb])

    if not stage1:
        return []

    # -------- Stage 2 --------
    prompt2 = format_prompt.replace("{extraction_json}", json.dumps(stage1, ensure_ascii=False))

    raw2 = _responses_text(prompt2)
    parsed2 = json.loads(_extract_json_substring(raw2))

    if isinstance(parsed2, dict) and "variants" in parsed2:
        parsed2 = parsed2["variants"]

    if isinstance(parsed2, list):
        normed2 = [normalize_variant_keys(r) for r in parsed2 if isinstance(r, dict)]
        return expand_numeric_dn_columns(normed2)

    return stage1

