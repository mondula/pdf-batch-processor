# field_registry.py
import json
import os
from typing import Dict, List, Any

REGISTRY_FILENAME = "field_registry.json"

def _path(output_folder: str) -> str:
    return os.path.join(output_folder, REGISTRY_FILENAME)

def load_registry(output_folder: str) -> Dict[str, Any]:
    p = _path(output_folder)
    if not os.path.exists(p):
        return {"fields": []}
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "fields" not in data or not isinstance(data["fields"], list):
        data["fields"] = []
    return data

def save_registry(output_folder: str, registry: Dict[str, Any]) -> None:
    p = _path(output_folder)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

def get_known_fields(output_folder: str) -> List[str]:
    reg = load_registry(output_folder)
    # keep insertion order exactly
    fields = reg.get("fields", [])
    cleaned = []
    seen = set()
    for f in fields:
        s = str(f).strip()
        if s and s not in seen:
            cleaned.append(s)
            seen.add(s)
    return cleaned

def update_fields(output_folder: str, rows: List[Dict[str, Any]]) -> List[str]:
    reg = load_registry(output_folder)
    fields = reg.get("fields", [])
    seen = set([str(x).strip() for x in fields if str(x).strip()])

    new_fields = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        for k in r.keys():
            ks = str(k).strip()
            if ks and ks not in seen:
                seen.add(ks)
                fields.append(ks)
                new_fields.append(ks)

    if new_fields:
        reg["fields"] = fields
        save_registry(output_folder, reg)

    return new_fields
