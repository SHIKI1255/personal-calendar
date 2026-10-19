"""Read-only, searchable catalog of effective calendar configuration."""
import argparse
import json
from pathlib import Path

from calendar_core import ROOT, CATEGORIES, load_inputs, catalog_entries


def search_catalog(entries, category=None, search=""):
    query = search.strip().casefold()
    return [row for row in entries if (not category or row["category"] == category) and
            (not query or query in " ".join(str(row[key]) for key in
             ("key", "name", "category", "category_name", "subgroup")).casefold())]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--category", choices=list(CATEGORIES))
    parser.add_argument("--search", default="", help="Chinese name, stable ID, category or subgroup")
    parser.add_argument("--json", action="store_true", help="Machine-readable catalog; does not write files")
    args = parser.parse_args()
    config, rules = load_inputs(args.config)
    rows = search_catalog(catalog_entries(config, rules), args.category, args.search)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            state = "已启用" if row["enabled"] else "已关闭：" + row["disabled_reason"]
            print(f"{row['category_name']} | {row['name']} | {row['key']} | {state}")
            print(f"  {row['description']}")
            print(f"  单项开关：{row['config_key']} 中的 {row['id']}；归属：{', '.join(row['feeds'])}")
