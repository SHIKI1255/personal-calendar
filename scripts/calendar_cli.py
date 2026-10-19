"""Build a complete candidate site offline, outside the repository."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import shutil

from calendar_core import (ROOT, FEEDS, CATEGORY_REGISTRY, digest, canonical, load_inputs,
                           make_feeds, render_feeds, catalog_entries)
from build_compat import load_probe, render_calendar, render_grouped_candidate, FEED, CANDIDATE_FEED
from validate_calendar import validate_ics


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def render_index(config, catalog, window, base_url):
    esc = html.escape
    cards, rows, options = [], [], []
    for group in CATEGORY_REGISTRY:
        entries = [r for r in catalog if r["category"] == group["id"]]
        enabled = sum(r["enabled"] for r in entries)
        state = f"{enabled} / {len(entries)} 条规则已启用" if config["categories"][group["id"]] else "分类已关闭 · 地址保留为空日历"
        url = base_url + "/" + group["feed"]
        cards.append(f'<article class="card"><h3>{esc(group["name"])}</h3>'
                     f'<p class="muted">{esc(state)}</p><p>{esc("、".join(r["name"] for r in entries))}</p>'
                     f'<a class="button secondary" href="{esc(url.replace("https:", "webcal:", 1))}">订阅此分类</a>'
                     f'<a href="{esc(group["feed"])}">ICS 地址</a></article>')
        options.append(f'<option value="{esc(group["id"])}">{esc(group["name"])}</option>')
    for row in catalog:
        search = " ".join(str(row[key]) for key in ("key", "name", "category", "category_name", "subgroup"))
        state = "已启用" if row["enabled"] else "已关闭：" + row["disabled_reason"]
        links = " · ".join(f'<a href="{esc(name)}">{esc(name)}</a>' for name in row["feeds"])
        rows.append(f'<tr data-category="{esc(row["category"])}" data-search="{esc(search)}">'
                    f'<td>{esc(row["category_name"])}</td><td>{esc(row["name"])}</td><td>{esc(state)}</td>'
                    f'<td>{esc(row["description"]).replace(chr(10), "<br>")}</td>'
                    f'<td><code>{esc(row["key"])}</code><br><code>{esc(row["config_key"])}</code><br>{links}</td></tr>')
    template = (ROOT / "web/index.html").read_text(encoding="utf-8")
    for key, value in {"YEARS": f"{window[0]}—{window[1]}", "BASE": esc(base_url),
                       "WEBCAL": esc(base_url.replace("https:", "webcal:", 1)),
                       "CARDS": "\n".join(cards), "RULES": "\n".join(rows),
                       "OPTIONS": "\n".join(options), "TOTAL": str(len(catalog))}.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def build(output, state_output, now, config_path=ROOT / "config.toml", state_path=ROOT / "state/events.json"):
    output, state_output = Path(output).resolve(), Path(state_output).resolve()
    for path in (output, state_output):
        if path == ROOT or ROOT in path.parents:
            raise ValueError("Candidate output must stay outside the source repository")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a new empty candidate directory; never overwrite a last-good build")
    config, rules = load_inputs(config_path)
    previous = json.loads(Path(state_path).read_text(encoding="utf-8")) if Path(state_path).exists() else {}
    feeds, window = make_feeds(config, rules, now)
    rendered, state = render_feeds(feeds, previous, now)
    counts = {name: validate_ics(raw, feeds[name]) for name, raw in rendered.items()}
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if set(manifest["production_feeds"]) != set(FEEDS):
        raise ValueError("Publication manifest does not match the feed registry")
    catalog = catalog_entries(config, rules)
    template = render_index(config, catalog, window, manifest["public_base_url"])
    # All validation precedes filesystem publication. Exceptions cannot overwrite a good site.
    output.mkdir(parents=True, exist_ok=True)
    for name, raw in rendered.items():
        (output / name).write_bytes(raw)
    (output / "index.html").write_text(template, encoding="utf-8", newline="\n")
    (output / "catalog.js").write_text((ROOT / "web/catalog.js").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    write_json(output / "catalog.json", catalog)
    (output / ".nojekyll").write_bytes(b"")
    # Frozen probes remain at their old URLs. No new schedule data is fetched or produced.
    probe = load_probe()
    (output / "compatibility").mkdir()
    (output / FEED).write_bytes(render_calendar(probe))
    (output / CANDIDATE_FEED).write_bytes(render_grouped_candidate(probe))
    for filename in (probe["source_snapshot"], probe["source_metadata"]):
        shutil.copyfile(ROOT / "data/compatibility" / filename, output / "compatibility" / filename)
        if filename.endswith('.json'):
            # Git normalizes source JSON; normalize old Windows working copies too.
            target = output / "compatibility" / filename
            target.write_text(target.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    # Pages' artifact uploader excludes hidden marker files from the public tar.
    files = {p.relative_to(output).as_posix(): digest(p.read_bytes()) for p in sorted(output.rglob("*"))
             if p.is_file() and not p.name.startswith('.')}
    report = {"schema": 1, "phase": "festivals_and_solar_terms", "years": list(window),
              "event_counts": counts, "files": files, "release": digest(canonical(files)),
              "categories": [{**group, "enabled": config["categories"][group["id"]],
                              "enabled_rules": sum(r["enabled"] for r in catalog if r["category"] == group["id"])}
                             for group in CATEGORY_REGISTRY],
              "native_badges": "cancelled", "device_acceptance": manifest["device_acceptance"],
              "hko_reference_years": [2023, 2029], "algorithm": "lunar_python==1.4.8",
              "frozen_probes": "both_user_reported_no_badges; unsubscribe"}
    write_json(output / "status.json", report)
    write_json(state_output, state)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--state", type=Path, default=ROOT / "state/events.json")
    parser.add_argument("--as-of", help="ISO date-time with timezone, for reproducible checks")
    args = parser.parse_args()
    instant = datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc)
    print(json.dumps(build(args.output, args.state_output, instant, args.config, args.state), ensure_ascii=True, indent=2))
