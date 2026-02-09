# export.py
import pandas as pd
from typing import Any, Dict, List, Union, Optional

# Priority columns first in the exported CSV.
# Keep this list stable to avoid column churn across runs.
DEFAULT_PRIORITY = ["Manufacturer", "Source PDF", "Source PDF Path", "DN"]

def _as_rows(data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []

def export_to_csv(
    data,
    output_path: str,
    column_order: Optional[List[str]] = None,
    priority_cols: Optional[List[str]] = None,
):
    rows = _as_rows(data)
    if not rows:
        print("No valid data to export (empty).")
        return

    # build union of keys (stable order)
    seen = []
    seen_set = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_set:
                seen.append(k)
                seen_set.add(k)

    # priority first (always)
    priority = priority_cols or DEFAULT_PRIORITY
    ordered = []
    for k in priority:
        if k in seen_set and k not in ordered:
            ordered.append(k)

    # then: use registry order if provided
    if column_order:
        for k in column_order:
            if k in seen_set and k not in ordered:
                ordered.append(k)

    # then: remaining in first-seen order
    for k in seen:
        if k not in ordered:
            ordered.append(k)

    # normalize missing values
    normalized = []
    for r in rows:
        nr = {}
        for k in ordered:
            v = r.get(k, "N/A")
            if v is None:
                v = "N/A"
            nr[k] = v
        normalized.append(nr)

    df = pd.DataFrame(normalized, columns=ordered)
    df = df.fillna("N/A")
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"CSV saved: {output_path}")
