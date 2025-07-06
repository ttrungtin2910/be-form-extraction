import json
import pandas as pd
from pathlib import Path

def save_json_to_file(data: dict, file_path: str | Path, ensure_ascii: bool = False, indent: int = 2) -> None:
    """
    Save a Python dictionary as a JSON file.

    :param data: Dictionary to save
    :param file_path: Output file path (str or Path)
    :param ensure_ascii: If False, keeps Unicode characters (e.g., tiếng Việt); if True, escapes them
    :param indent: Indentation level for pretty-printing
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)

def flatten_json(json_obj: dict) -> dict:
    flat = {}
    for key, value in json_obj.items():
        if isinstance(value, dict):
            for sub_key, sub_val in value.items():
                flat[f"{key}.{sub_key}"] = sub_val
        elif isinstance(value, list):
            for i, item in enumerate(value):
                flat[f"{key}_{i+1}"] = item
        else:
            flat[key] = value
    return flat

def export_json_list_to_excel(json_list: list[dict], output_path: str | Path = "output.xlsx"):
    flattened = [flatten_json(record) for record in json_list]
    df = pd.DataFrame(flattened)
    df.to_excel(output_path, index=False)
    print(f"✅ Excel saved: {output_path}")