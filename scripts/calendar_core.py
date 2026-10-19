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
CATEGORY_REGISTRY = json.loads((ROOT / "data/categories.json").read_text(encoding="utf-8"))
CATEGORIES = {r["id"]: r["name"] for r in CATEGORY_REGISTRY}
FESTIVAL_CATEGORIES = {r["id"] for r in CATEGORY_REGISTRY if r["section"] == "festivals"}
TERMS = json.loads((ROOT / "data/solar_terms.json").read_text(encoding="utf-8"))
SEASONAL_RULES = json.loads((ROOT / "data/seasonal.json").read_text(encoding="utf-8"))
FEEDS = {"calendar.ics": "节日、节气与季节节点", "festivals.ics": "节日合集（兼容订阅）",
         **{r["feed"]: r["name"] for r in CATEGORY_REGISTRY}}
TERM_DESCRIPTION = "按太阳黄经计算，取北京时间所属日期；只展示日期。"


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_inputs(config_path=ROOT / "config.toml", rules_path=ROOT / "data/festivals.json"):
    config = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
    if len(CATEGORIES) != len(CATEGORY_REGISTRY) or len(FEEDS) != len(CATEGORIES) + 2:
        raise ValueError("Duplicate category or feed")
    for category in CATEGORY_REGISTRY:
        if not re.fullmatch(r"[a-z][a-z_]*", category["id"]) or category["feed"] != category["id"] + ".ics":
            raise ValueError("Invalid category/feed identity")
        if category["section"] not in ("festivals", "solar_terms", "seasonal"):
            raise ValueError("Invalid category section")
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
        if rule["category"] not in FESTIVAL_CATEGORIES or not rule["name"]:
            raise ValueError("Invalid festival category/name")
        if rule["type"] not in {"fixed", "lunar", "lunar_eve", "solar_term", "nth_weekday", "relative", "easter"}:
            raise ValueError("Unknown festival rule")
        if rule["type"] == "relative" and rule["base"] not in ids:
            raise ValueError("Unknown relative date base")
        if rule.get("optional") not in (None, "easter_monday") or rule.get("region") not in (None, "north", "south"):
            raise ValueError("Unknown festival option/region")
    seasonal_ids = [r["id"] for r in SEASONAL_RULES]
    if len(set(seasonal_ids)) != len(seasonal_ids):
        raise ValueError("Duplicate seasonal identity")
    for rule in SEASONAL_RULES:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", rule["id"]) or not rule["name"]:
            raise ValueError("Invalid seasonal identity/name")
        if rule["group"] == "sanfu":
            if rule["stage"] not in ("initial", "middle", "final", "end"):
                raise ValueError("Unknown sanfu stage")
        elif rule["group"] == "shujiu":
            if type(rule["offset"]) is not int or rule["offset"] not in range(0, 82, 9):
                raise ValueError("Invalid shujiu offset")
        else:
            raise ValueError("Unknown seasonal group")
    if any(type(config["seasonal"][key]) is not bool for key in ("sanfu", "shujiu")):
        raise ValueError("Invalid seasonal subgroup switches")
    for section, allowed in (("festivals", set(ids)), ("solar_terms", set(TERMS)), ("seasonal", set(seasonal_ids))):
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


def disabled_reason(config, section, identity, category, rule=None):
    """One effective-switch policy for generation, CLI and the public catalog."""
    if not config["categories"][category]:
        return "分类已关闭"
    if identity in config[section]["disabled_ids"]:
        return "单项已关闭"
    rule = rule or {}
    if rule.get("optional") and not config["festivals"][rule["optional"]]:
        return "专用开关已关闭"
    if rule.get("region") and config["festivals"]["little_new_year"] not in ("both", rule["region"]):
        return "地域选项未启用"
    if section == "seasonal" and not config["seasonal"][rule["group"]]:
        return "季节子组已关闭"
    return ""


def nth_geng(start, n):
    """Civil-day counting is inclusive; do not use 23:00 astrology day changes."""
    for offset in range(10 * n):
        day = start + timedelta(days=offset)
        if Solar.fromYmd(day.year, day.month, day.day).getLunar().getDayGan() == "庚":
            n -= 1
            if n == 0:
                return day
    raise ValueError("Unable to locate geng day")


@lru_cache(maxsize=128)
def sanfu(year):
    terms = solar_terms(year)
    result = {"initial": nth_geng(terms["xiazhi"], 3),
              "middle": nth_geng(terms["xiazhi"], 4),
              "final": nth_geng(terms["liqiu"], 1)}
    result["end"] = result["final"] + timedelta(days=10)
    if (result["middle"] - result["initial"]).days != 10 or (result["final"] - result["middle"]).days not in (10, 20):
        raise ValueError("Invalid sanfu stage lengths")
    return result


def seasonal_rule_description(rule):
    if rule["group"] == "sanfu":
        return {"initial": "夏至当天起第三个庚日；初伏开始，共10天。",
                "middle": "夏至当天起第四个庚日；中伏开始，持续10或20天。",
                "final": "立秋当天起第一个庚日；末伏开始，共10天。",
                "end": "末伏开始后第10天；末伏结束后的第一天。"}[rule["stage"]] + "节气当天为庚日时计入。"
    if rule["offset"] == 81:
        return "冬至后第81天；九九结束后的第一天。"
    return f"从冬至当天起计，每九天一阶段；冬至后第{rule['offset']}天开始，本阶段共9天。"


def catalog_entries(config, rules):
    rows = []
    definitions = [("festivals", r["id"], r["name"], r["category"], rule_description(r), r) for r in rules]
    definitions += [("solar_terms", key, name, "solar_terms", TERM_DESCRIPTION, {}) for key, name in TERMS.items()]
    definitions += [("seasonal", r["id"], r["name"], "seasonal", seasonal_rule_description(r), r) for r in SEASONAL_RULES]
    for section, identity, name, category, description, rule in definitions:
        group = next(r for r in CATEGORY_REGISTRY if r["id"] == category)
        reason = disabled_reason(config, section, identity, category, rule)
        feeds = ["calendar.ics", group["feed"]]
        if section == "festivals":
            feeds.append("festivals.ics")
        rows.append({"key": section + ":" + identity, "id": identity, "name": name,
                     "category": category, "category_name": group["name"], "section": section,
                     "config_key": section + ".disabled_ids", "enabled": not reason,
                     "disabled_reason": reason, "description": description, "feeds": feeds,
                     "subgroup": rule.get("group", ""), "source_url": rule.get("source_url", "")})
    order = {key: i for i, key in enumerate(CATEGORIES)}
    # Stable definition order keeps solar terms and seasonal stages chronological.
    return sorted(rows, key=lambda r: order[r["category"]])


def make_feeds(config, rules, now):
    first, last = year_window(now, config)
    lower, upper = date(first, 1, 1), date(last + 1, 1, 1)
    definitions = {r["id"]: r for r in rules}
    by_category = {key: [] for key in CATEGORIES}
    for rule in rules:
        if disabled_reason(config, "festivals", rule["id"], rule["category"], rule):
            continue
        lunar = rule["type"] in ("lunar", "lunar_eve")
        for year in range(first - 1, last + 2):
            start = rule_date(rule, year, definitions)
            if lower <= start < upper:
                identity = f"{rule['id']}-{'l' if lunar else 'g'}{year}"
                by_category[rule["category"]].append(Event(identity, start, rule["name"], rule_description(rule), (CATEGORIES[rule["category"]],)))
    terms = by_category["solar_terms"]
    for key, name in TERMS.items():
        if disabled_reason(config, "solar_terms", key, "solar_terms"):
            continue
        for year in range(first, last + 1):
            start = solar_terms(year)[key]
            identity = f"{'qingming' if key == 'qingming' else 'term-' + key}-g{year}"
            terms.append(Event(identity, start, name, TERM_DESCRIPTION, (CATEGORIES["solar_terms"],)))
    for rule in SEASONAL_RULES:
        if disabled_reason(config, "seasonal", rule["id"], "seasonal", rule):
            continue
        for year in range(first - 1, last + 1):
            description = seasonal_rule_description(rule)
            if rule["group"] == "sanfu":
                stages = sanfu(year)
                start = stages[rule["stage"]]
                if rule["stage"] == "middle":
                    description += f"本年中伏{(stages['final'] - stages['middle']).days}天。"
            else:
                start = solar_terms(year)["dongzhi"] + timedelta(days=rule["offset"])
                description += f"所属数九周期始于{year}年冬至。"
            if lower <= start < upper:
                description += "\n仅表示历法民俗节点，不是当地天气预报，不表示放假或补班。"
                by_category["seasonal"].append(Event(f"{rule['id']}-g{year}", start, rule["name"], description, (CATEGORIES["seasonal"],)))
    festivals = [event for key in CATEGORIES if key in FESTIVAL_CATEGORIES for event in by_category[key]]
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
    for event in by_category["seasonal"]:
        if event.identity in combined:
            raise ValueError("Seasonal identity collides with a festival")
        combined[event.identity] = event
    result = {"calendar.ics": list(combined.values()), "festivals.ics": festivals,
              **{r["feed"]: by_category[r["id"]] for r in CATEGORY_REGISTRY}}
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
