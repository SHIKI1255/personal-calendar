"""Read HKO text snapshots independently, never deriving expectations with lunar_python."""
from datetime import date, timedelta
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).parent / "fixtures/hko"
MONTHS = {name: i for i, name in enumerate("正 二 三 四 五 六 七 八 九 十 十一 十二".split(), 1)}
DAYS = {name: i for i, name in enumerate("初一 初二 初三 初四 初五 初六 初七 初八 初九 初十 十一 十二 十三 十四 十五 十六 十七 十八 十九 二十 廿一 廿二 廿三 廿四 廿五 廿六 廿七 廿八 廿九 三十".split(), 1)}
SIMPLIFIED = str.maketrans({"驚": "惊", "蟄": "蛰", "穀": "谷", "處": "处", "滿": "满", "種": "种"})


def read_reference():
    rows, terms = {}, {}
    lunar_year = month = None
    leap = False
    for source in json.loads((ROOT / "sources.json").read_text(encoding="utf-8")):
        year = source["year"]
        raw = (ROOT / f"{year}.txt").read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("HKO fixture hash mismatch")
        parsed = 0
        for line in raw.decode("utf-8-sig").splitlines():
            match = re.match(r"^(\d{4})年(\d+)月(\d+)日\s+(\S+)\s+星期\S+(?:\s+(\S+))?\s*$", line)
            if not match:
                continue
            y, m, d, token, term = match.groups()
            day = date(int(y), int(m), int(d))
            parsed += 1
            if "月" in token:
                leap = token.startswith("閏")
                month = MONTHS[token.removeprefix("閏").removesuffix("月")]
                if month == 1 and not leap:
                    lunar_year = day.year
                elif lunar_year is None:
                    lunar_year = day.year - 1
                lunar_day = 1
            else:
                lunar_day = DAYS[token]
            if lunar_year is not None:
                rows[day] = (lunar_year, -month if leap else month, lunar_day)
            if term:
                terms[day] = term.translate(SIMPLIFIED)
        expected = (date(year + 1, 1, 1) - date(year, 1, 1)).days
        if parsed != expected:
            raise ValueError(f"HKO fixture {year}: parsed {parsed}, expected {expected}")
    return rows, terms
