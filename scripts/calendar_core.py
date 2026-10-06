"""Offline dates, stable identities and RFC 5545 output. No calendar data fetches."""
from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import tomllib
from zoneinfo import ZoneInfo

from lunar_python import Lunar, Solar
from build_compat import fold, text_escape

ROOT = Path(__file__).resolve().parents[1]
ZONE = ZoneInfo("Asia/Shanghai")
CATEGORIES = {"traditional": "传统节日", "common": "常见节日", "holy_week": "圣周", "solar_terms": "二十四节气"}
TERMS = dict(zip(
    "xiaohan dahan lichun yushui jingzhe chunfen qingming guyu lixia xiaoman mangzhong xiazhi xiaoshu dashu liqiu chushu bailu qiufen hanlu shuangjiang lidong xiaoxue daxue dongzhi".split(),
    "小寒 大寒 立春 雨水 惊蛰 春分 清明 谷雨 立夏 小满 芒种 夏至 小暑 大暑 立秋 处暑 白露 秋分 寒露 霜降 立冬 小雪 大雪 冬至".split()))
FEEDS = {"calendar.ics": "节日与二十四节气", "festivals.ics": "常规节日与圣周", "solar_terms.ics": "二十四节气"}


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_inputs(config_path=ROOT / "config.toml", rules_path=ROOT / "data/festivals.json"):
    config = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
    if config["timezone"] != "Asia/Shanghai":
        raise ValueError("Lunar/solar algorithm is defined in Beijing time; timezone must be Asia/Shanghai")
    for key in ("past_years", "future_years"):
        if type(config[key]) is not int or not 0 <= config[key] <= 30:
            raise ValueError("Invalid year window")
    if set(config["categories"]) != set(CATEGORIES) or any(type(v) is not bool for v in config["categories"].values()):
        raise ValueError("Invalid category switches")
    if config["festivals"]["little_new_year"] not in ("both", "north", "south", "none"):
        raise ValueError("Invalid little_new_year option")
    if type(config["festivals"]["easter_monday"]) is not bool:
        raise ValueError("easter_monday must be boolean")
    ids = [r["id"] for r in rules]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[a-z][a-z0-9-]*", x) for x in ids):
        raise ValueError("Invalid or duplicate festival identity")
    for rule in rules:
        if rule["category"] not in ("traditional", "common", "holy_week") or not rule["name"]:
            raise ValueError("Invalid festival category/name")
        if rule["type"] not in {"fixed", "lunar", "lunar_eve", "solar_term", "nth_weekday", "relative", "easter"}:
            raise ValueError("Unknown festival rule")
        if rule["type"] == "relative" and rule["base"] not in ids:
            raise ValueError("Unknown relative date base")
    for section, allowed in (("festivals", set(ids)), ("solar_terms", set(TERMS))):
        disabled = config[section]["disabled_ids"]
        if not isinstance(disabled, list) or any(not isinstance(x, str) for x in disabled) or not set(disabled) <= allowed:
            raise ValueError("Unknown disabled identity in " + section)
    return config, rules


def year_window(now: datetime, config: dict):
    if now.tzinfo is None:
        raise ValueError("An explicit timezone is required")
    year = now.astimezone(ZONE).year
    return year - config["past_years"], year + config["future_years"]


def nth_weekday(year, month, weekday, nth):
    if not (0 <= weekday <= 6 and 1 <= nth <= 5):
        raise ValueError("Invalid weekday ordinal")
    first = date(year, month, 1)
    result = first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (nth - 1))
    if result.month != month:
        raise ValueError("Weekday occurrence does not exist in month")
    return result


def easter(year):
    """Oudin's Gregorian computus, USNO / Explanatory Supplement (1940/2012)."""
    c = year // 100
    n = year % 19
    k = (c - 17) // 25
    i = (c - c // 4 - (c - k) // 3 + 19 * n + 15) % 30
    i -= (i // 28) * (1 - (i // 28) * (29 // (i + 1)) * ((21 - n) // 11))
    j = (year + year // 4 + i + 2 - c + c // 4) % 7
    length = i - j
    month = 3 + (length + 40) // 44
    day = length + 28 - 31 * (month // 4)
    return date(year, month, day)


def lunar_date(year, month, day):
    # Positive month means the regular month, never the library's negative leap month.
    if month <= 0:
        raise ValueError("Leap-month festivals are not generated")
    return date.fromisoformat(Lunar.fromYmd(year, month, day).getSolar().toYmd())


@lru_cache(maxsize=128)
def solar_terms(year):
    table = Solar.fromYmd(year, 7, 1).getLunar().getJieQiTable()
    result = {}
    for identity, name in TERMS.items():
        # Chinese 冬至 is the previous year's solstice in this library's table.
        key = "DONG_ZHI" if identity == "dongzhi" else name
        result[identity] = date.fromisoformat(table[key].toYmd())
    if len(set(result.values())) != 24 or any(d.year != year for d in result.values()):
        raise ValueError("Solar-term table does not cover exactly this Gregorian year")
    return result


@dataclass(frozen=True)
class Event:
    identity: str
    start: date
    title: str
    description: str
    categories: tuple[str, ...]

    @property
    def uid(self):
        return self.identity + "@personal-calendar.shiki1255.github.io"

    def payload(self):
        return {"identity": self.identity, "date": self.start.isoformat(), "title": self.title,
                "description": self.description, "categories": list(self.categories)}


def rule_date(rule, year, definitions, visiting=()):
    if rule["id"] in visiting:
        raise ValueError("Cyclic relative festival rule")
    kind = rule["type"]
    if kind == "fixed":
        return date(year, rule["month"], rule["day"])
    if kind == "nth_weekday":
        return nth_weekday(year, rule["month"], rule["weekday"], rule["nth"])
    if kind == "easter":
        return easter(year) + timedelta(days=rule["offset"])
    if kind == "relative":
        base = definitions[rule["base"]]
        if base["type"] in ("lunar", "lunar_eve"):
            raise ValueError("Relative rules require a Gregorian-year base")
        return rule_date(base, year, definitions, visiting + (rule["id"],)) + timedelta(days=rule["offset"])
    if kind == "lunar":
        return lunar_date(year, rule["month"], rule["day"])
    if kind == "lunar_eve":
        return lunar_date(year + 1, 1, 1) - timedelta(days=1)
    if kind == "solar_term":
        return solar_terms(year)[rule["term"]]
    raise ValueError("Unknown date rule")


def rule_description(rule):
    kind = rule["type"]
    if kind == "lunar":
        result = f"农历{rule['month']}月{rule['day']}日；闰月不重复。"
    elif kind == "lunar_eve":
        result = "下一次春节的前一天；不固定为农历十二月三十。"
    elif kind == "fixed":
        result = f"公历{rule['month']}月{rule['day']}日。"
    elif kind == "nth_weekday":
        result = f"每年{rule['month']}月第{rule['nth']}个星期{'一二三四五六日'[rule['weekday']]}。"
    elif kind == "easter":
        result = f"西方公历复活节算法；相对复活节偏移{rule['offset']}天。"
    elif kind == "relative":
        result = f"相对{rule['base']}偏移{rule['offset']}天。"
    else:
        result = "当年清明节气在北京时间对应的日期。"
    return result + rule.get("note", "") + "\n节日本体，不表示放假或补班安排。"


def make_feeds(config, rules, now):
    first, last = year_window(now, config)
    lower, upper = date(first, 1, 1), date(last + 1, 1, 1)
    definitions = {r["id"]: r for r in rules}
    festivals, terms = [], []
    for rule in rules:
        if not config["categories"][rule["category"]] or rule["id"] in config["festivals"]["disabled_ids"]:
            continue
        if rule.get("optional") and not config["festivals"][rule["optional"]]:
            continue
        region = rule.get("region")
        if region and config["festivals"]["little_new_year"] not in ("both", region):
            continue
        lunar = rule["type"] in ("lunar", "lunar_eve")
        for year in range(first - 1, last + 2):
            start = rule_date(rule, year, definitions)
            if lower <= start < upper:
                identity = f"{rule['id']}-{'l' if lunar else 'g'}{year}"
                festivals.append(Event(identity, start, rule["name"], rule_description(rule), (CATEGORIES[rule["category"]],)))
    if config["categories"]["solar_terms"]:
        for year in range(first, last + 1):
            for key, start in solar_terms(year).items():
                if key in config["solar_terms"]["disabled_ids"]:
                    continue
                identity = f"{'qingming' if key == 'qingming' else 'term-' + key}-g{year}"
                terms.append(Event(identity, start, TERMS[key], "按太阳黄经计算，取北京时间所属日期；只展示日期。", (CATEGORIES["solar_terms"],)))
    combined = {e.identity: e for e in festivals}
    for event in terms:
        if event.identity in combined:
            old = combined[event.identity]
            if old.start != event.start:
                raise ValueError("Qingming festival/term disagree")
            combined[event.identity] = replace(old, description=old.description + "\n" + event.description,
                                               categories=old.categories + event.categories)
        else:
            combined[event.identity] = event
    result = {"calendar.ics": list(combined.values()), "festivals.ics": festivals, "solar_terms.ics": terms}
    for events in result.values():
        if len({e.uid for e in events}) != len(events):
            raise ValueError("Duplicate UID")
        events.sort(key=lambda e: (e.start, e.identity))
    return result, (first, last)


def render_feeds(feeds, previous, now):
    state = copy.deepcopy(previous)
    state.setdefault("schema", 1)
    if state["schema"] != 1:
        raise ValueError("Unsupported revision state schema")
    entries = state.setdefault("events", {})
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = {}
    for filename, events in feeds.items():
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//SHIKI1255//Personal Calendar//ZH",
                 "CALSCALE:GREGORIAN", "X-WR-CALNAME:" + FEEDS[filename], "X-WR-TIMEZONE:Asia/Shanghai"]
        for event in events:
            key = filename + "/" + event.identity
            content_hash = digest(canonical(event.payload()))
            old = entries.get(key)
            if old is None:
                revision = {"hash": content_hash, "created": stamp, "modified": stamp, "sequence": 0}
            elif old["hash"] == content_hash:
                revision = old
            else:
                if stamp < old["modified"]:
                    raise ValueError("Revision timestamp moved backwards")
                revision = {"hash": content_hash, "created": old["created"], "modified": stamp, "sequence": old["sequence"] + 1}
            entries[key] = revision
            lines.extend(["BEGIN:VEVENT", "UID:" + event.uid, "DTSTAMP:" + revision["modified"],
                          "CREATED:" + revision["created"], "LAST-MODIFIED:" + revision["modified"],
                          "SEQUENCE:" + str(revision["sequence"]), f"DTSTART;VALUE=DATE:{event.start:%Y%m%d}",
                          f"DTEND;VALUE=DATE:{event.start + timedelta(days=1):%Y%m%d}",
                          "SUMMARY;LANGUAGE=zh-CN:" + text_escape(event.title),
                          "DESCRIPTION:" + text_escape(event.description),
                          "CATEGORIES:" + ",".join(text_escape(c) for c in event.categories),
                          "CLASS:PUBLIC", "TRANSP:TRANSPARENT", "END:VEVENT"])
        lines.append("END:VCALENDAR")
        output[filename] = b"\r\n".join(fold(line) for line in lines) + b"\r\n"
    return output, state
