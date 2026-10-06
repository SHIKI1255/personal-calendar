"""Build a complete candidate site offline, outside the repository."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import shutil

from calendar_core import ROOT, FEEDS, TERMS, digest, canonical, load_inputs, make_feeds, render_feeds, rule_description
from build_compat import load_probe, render_calendar, render_grouped_candidate, FEED, CANDIDATE_FEED
from validate_calendar import validate_ics


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    # All validation precedes filesystem publication. Exceptions cannot overwrite a good site.
    output.mkdir(parents=True, exist_ok=True)
    for name, raw in rendered.items():
        (output / name).write_bytes(raw)
    rows = "\n".join(f"<tr><td>{html.escape(r['name'])}</td><td>{html.escape(rule_description(r))}</td><td><code>{r['id']}</code></td></tr>" for r in rules)
    template = (ROOT / "web/index.html").read_text(encoding="utf-8")
    template = template.replace("{{YEARS}}", f"{window[0]}—{window[1]}").replace("{{RULES}}", rows)
    template = template.replace("{{TERMS}}", "、".join(TERMS.values()))
    (output / "index.html").write_text(template, encoding="utf-8")
    (output / ".nojekyll").write_bytes(b"")
    # Frozen probes remain at their old URLs. No new schedule data is fetched or produced.
    probe = load_probe()
    (output / "compatibility").mkdir()
    (output / FEED).write_bytes(render_calendar(probe))
    (output / CANDIDATE_FEED).write_bytes(render_grouped_candidate(probe))
    for filename in (probe["source_snapshot"], probe["source_metadata"]):
        shutil.copyfile(ROOT / "data/compatibility" / filename, output / "compatibility" / filename)
    # Pages' artifact uploader excludes hidden marker files from the public tar.
    files = {p.relative_to(output).as_posix(): digest(p.read_bytes()) for p in sorted(output.rglob("*"))
             if p.is_file() and not p.name.startswith('.')}
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    report = {"schema": 1, "phase": "festivals_and_solar_terms", "years": list(window),
              "event_counts": counts, "files": files, "release": digest(canonical(files)),
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
