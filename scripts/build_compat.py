"""Build the gated Apple badge probe, offline and deterministically."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://shiki1255.github.io/personal-calendar"
FEED = "compatibility/apple-badges.ics"
CANDIDATE_FEED = "compatibility/apple-badges-b1.ics"
BADGES = {"holiday": "WORK-HOLIDAY", "workday": "ALTERNATE-WORKDAY"}


def text_escape(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("\r\n", "\n")
            .replace("\r", "\n").replace("\n", "\\n")
            .replace(";", "\\;").replace(",", "\\,"))


def fold(line: str) -> bytes:
    """75 octets per physical line, without splitting a UTF-8 code point."""
    result, current = [], bytearray()
    for char in line:
        chunk = char.encode("utf-8")
        if len(current) + len(chunk) > 75:
            result.append(bytes(current))
            current = bytearray(b" ")
        current.extend(chunk)
    result.append(bytes(current))
    return b"\r\n".join(result)


def load_probe() -> dict:
    folder = ROOT / "data/compatibility"
    probe = json.loads((folder / "probe.json").read_text(encoding="utf-8"))
    snapshot = (folder / probe["source_snapshot"]).read_bytes()
    metadata = json.loads((folder / probe["source_metadata"]).read_text(encoding="utf-8"))
    if hashlib.sha256(snapshot).hexdigest() != metadata["sha256"]:
        raise ValueError("Official source snapshot hash mismatch")
    if metadata["source_url"] != probe["source_url"]:
        raise ValueError("Official source identity mismatch")
    content = snapshot.decode("utf-8")
    for evidence in (probe["source_title"], probe["document_number"],
                     "10月1日（周四）至7日（周三）放假调休，共7天。",
                     "9月20日（周日）、10月10日（周六）上班。"):
        if evidence not in content:
            raise ValueError("Missing source evidence: " + evidence)
    if probe["revision"] not in (1, 2):
        raise ValueError("Probe only supports reviewed revisions 1 and 2")
    for key in ("created_at", "modified_at"):
        datetime.strptime(probe[key], "%Y%m%dT%H%M%SZ")
    if probe["modified_at"] < probe["created_at"]:
        raise ValueError("Modification precedes creation")
    expected = {"2026-10-07": "holiday", "2026-10-09": "control",
                "2026-10-10": "workday", "2026-10-11": "control"}
    if len(probe["events"]) != 4 or {e["date"]: e["kind"] for e in probe["events"]} != expected:
        raise ValueError("Probe differs from reviewed official dates and controls")
    return probe


def render_calendar(probe: dict) -> bytes:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SHIKI1255//Apple Badge Probe//ZH",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:班休角标兼容测试",
             "X-WR-TIMEZONE:Asia/Shanghai", "X-APPLE-LANGUAGE:zh", "X-APPLE-REGION:CN"]
    for event in sorted(probe["events"], key=lambda e: e["date"]):
        start = date.fromisoformat(event["date"])
        identity = str(uuid5(NAMESPACE_URL, BASE + "/probe/day/" + event["date"]))
        changing = bool(event.get("refresh_probe"))
        revision = probe["revision"] if changing else 1
        stamp = probe["modified_at"] if changing else probe["created_at"]
        title = event["title"] + (f" · r{revision}" if changing else "")
        if event["kind"] == "control":
            description = "兼容性对照事件；不设置班休角标，不代表个人排班。"
        else:
            description = "依据国务院办公厅2026年节假日安排；用于原生角标验证。"
        description += "\nSource: " + probe["source_url"]
        lines.extend(["BEGIN:VEVENT", f"UID:{identity}@personal-calendar",
                      f"X-APPLE-UNIVERSAL-ID:{identity}", f"DTSTAMP:{stamp}",
                      f"CREATED:{probe['created_at']}", f"LAST-MODIFIED:{stamp}",
                      f"SEQUENCE:{revision - 1}", f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
                      f"DTEND;VALUE=DATE:{start + timedelta(days=1):%Y%m%d}",
                      "SUMMARY;LANGUAGE=zh-CN:" + text_escape(title),
                      "DESCRIPTION:" + text_escape(description),
                      "URL:" + probe["source_url"], "CLASS:PUBLIC", "TRANSP:TRANSPARENT",
                      "CATEGORIES:" + ("兼容性对照" if event["kind"] == "control" else "中国节假日")])
        if event["kind"] in BADGES:
            lines.append("X-APPLE-SPECIAL-DAY:" + BADGES[event["kind"]])
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return b"\r\n".join(fold(line) for line in lines) + b"\r\n"


def render_grouped_candidate(probe: dict) -> bytes:
    """Diagnostic B1: observed Apple metadata, independently sourced dates.

    This is not a production feed or an assertion that all properties cause badges.
    LANGUAGE=zh_CN mirrors Apple's legacy spelling ONLY in this diagnostic feed;
    the standards-oriented baseline keeps LANGUAGE=zh-CN. DTSTAMP remains a valid
    UTC DATE-TIME; Apple's DATE-valued stamp is deliberately not reproduced.
    New UIDs isolate B1 from the frozen r1 and Apple's official events.
    """
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SHIKI1255//Apple Badge Probe B1//ZH",
             "CALSCALE:GREGORIAN", "X-WR-CALNAME:中国大陆节假日",
             "X-APPLE-LANGUAGE:zh", "X-APPLE-REGION:CN"]
    group_id = str(uuid5(NAMESPACE_URL, BASE + "/probe-b/holiday/national-day"))
    # These dates are verified against the government snapshot in load_probe().
    events = [
        (date(2026, 10, 1), date(2026, 10, 8), "国庆节（休）", "holiday"),
        (date(2026, 10, 9), None, "普通日期对照 · B1", "control"),
        (date(2026, 10, 10), None, "国庆节（班）", "workday"),
        (date(2026, 10, 11), None, "普通周末对照 · B1", "control"),
    ]
    for start, end, title, kind in events:
        identity = str(uuid5(NAMESPACE_URL, BASE + "/probe-b/event/" + start.isoformat()))
        universal_id = group_id if kind in BADGES else identity
        lines.extend(["BEGIN:VEVENT", f"DTSTAMP:{probe['created_at']}", f"UID:{identity}",
                      f"DTSTART;VALUE=DATE:{start:%Y%m%d}"])
        # A DATE start without DTEND/DURATION means one day (RFC 5545 3.6.1).
        if end is not None:
            lines.append(f"DTEND;VALUE=DATE:{end:%Y%m%d}")
        lines.extend(["CLASS:PUBLIC", "SUMMARY;LANGUAGE=zh_CN:" + text_escape(title),
                      "TRANSP:TRANSPARENT", "CATEGORIES:節慶"])
        if kind in BADGES:
            lines.append("X-APPLE-SPECIAL-DAY:" + BADGES[kind])
        lines.extend(["X-APPLE-UNIVERSAL-ID:" + universal_id, "END:VEVENT"])
    lines.append("END:VCALENDAR")
    return b"\r\n".join(fold(line) for line in lines) + b"\r\n"


def build(output: Path) -> dict:
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("Build output must be outside the source repository")
    probe = load_probe()
    calendar = render_calendar(probe)
    output.mkdir(parents=True, exist_ok=True)
    target = output / FEED
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(calendar)
    candidate = render_grouped_candidate(probe)
    (output / CANDIDATE_FEED).write_bytes(candidate)
    template = (ROOT / "web/index.html").read_text(encoding="utf-8")
    (output / "index.html").write_text(template.replace("{{REVISION}}", html.escape(str(probe["revision"]))), encoding="utf-8")
    (output / ".nojekyll").write_bytes(b"")
    report = {"phase": "apple_badge_probe", "revision": probe["revision"],
              "device_acceptance": "pending", "event_count": 4,
              "feed": FEED, "sha256": hashlib.sha256(calendar).hexdigest(),
              "scheduled_data_updates": False,
              "baseline_device_result": "user_reported_events_visible_native_badges_absent",
              "candidate": {"profile": "B1", "feed": CANDIDATE_FEED,
                            "sha256": hashlib.sha256(candidate).hexdigest(),
                            "event_count": 4, "device_acceptance": "pending"}}
    (output / "status.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Only inert source text is published; never copy the government page's scripts.
    for filename in (probe["source_snapshot"], probe["source_metadata"]):
        shutil.copyfile(ROOT / "data/compatibility" / filename, output / "compatibility" / filename)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
