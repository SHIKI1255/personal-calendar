import copy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from icalendar import Calendar

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_compat import (ROOT, FEED, CANDIDATE_FEED, build, fold, load_probe,
                          render_calendar, render_grouped_candidate, text_escape)


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()
        self.raw = render_calendar(self.probe)
        self.calendar = Calendar.from_ical(self.raw)
        self.events = self.calendar.walk("VEVENT")

    def test_independent_parser_and_exact_dates(self):
        self.assertEqual(len(self.events), 4)
        self.assertEqual({e.decoded("DTSTART") for e in self.events},
                         {date(2026, 10, d) for d in (7, 9, 10, 11)})
        self.assertFalse(self.calendar.errors)
        for event in self.events:
            self.assertFalse(event.errors)

    def test_holiday_and_workday_extensions_only_on_official_dates(self):
        flags = {e.decoded("DTSTART"): str(e.get("X-APPLE-SPECIAL-DAY", "")) for e in self.events}
        self.assertEqual(flags, {date(2026, 10, 7): "WORK-HOLIDAY", date(2026, 10, 9): "",
                                 date(2026, 10, 10): "ALTERNATE-WORKDAY", date(2026, 10, 11): ""})

    def test_all_day_exclusive_end_and_no_alarm(self):
        for event in self.events:
            self.assertEqual(event["DTSTART"].params["VALUE"], "DATE")
            self.assertEqual(event.decoded("DTEND"), event.decoded("DTSTART") + timedelta(days=1))
            self.assertEqual(str(event["TRANSP"]), "TRANSPARENT")
            self.assertEqual(event.walk("VALARM"), [])

    def test_utf8_octet_folding_and_crlf(self):
        self.assertNotIn(b"\n", self.raw.replace(b"\r\n", b""))
        for line in self.raw.split(b"\r\n"):
            self.assertLessEqual(len(line), 75)
            line.decode("utf-8")
        value = "SUMMARY:" + "节气🙂" * 100
        folded = fold(value)
        self.assertEqual(folded.replace(b"\r\n ", b"").decode(), value)
        for line in folded.split(b"\r\n"):
            self.assertLessEqual(len(line), 75)

    def test_text_escaping_round_trip(self):
        value = "甲,乙;丙\\丁\n下一行"
        raw = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\n" + fold("SUMMARY:" + text_escape(value)) + b"\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
        self.assertEqual(str(Calendar.from_ical(raw).walk("VEVENT")[0]["SUMMARY"]), value)

    def test_deterministic_and_unique_uids(self):
        self.assertEqual(self.raw, render_calendar(self.probe))
        self.assertEqual(len({str(e["UID"]) for e in self.events}), 4)

    def test_revision_updates_one_event_without_changing_uid(self):
        initial = copy.deepcopy(self.probe)
        initial.update(revision=1, modified_at=initial["created_at"])
        updated = copy.deepcopy(initial)
        updated.update(revision=2, modified_at="20261007T000000Z")
        before = Calendar.from_ical(render_calendar(initial)).walk("VEVENT")
        after = Calendar.from_ical(render_calendar(updated)).walk("VEVENT")
        for old, new in zip(before, after):
            self.assertEqual(old["UID"], new["UID"])
            self.assertEqual(old["DTSTART"], new["DTSTART"])
            if old.decoded("DTSTART") == date(2026, 10, 9):
                self.assertEqual(new["SEQUENCE"], 1)
                self.assertIn("r2", str(new["SUMMARY"]))
                self.assertNotEqual(old["LAST-MODIFIED"], new["LAST-MODIFIED"])
            else:
                self.assertEqual(old.to_ical(), new.to_ical())

    def test_source_provenance(self):
        self.assertIn("beijing.gov.cn", self.probe["source_url"])
        self.assertEqual(self.probe["document_number"], "国办发明电〔2025〕7号")
        self.assertTrue(all(self.probe["source_url"] in str(e["DESCRIPTION"]) for e in self.events))

    def test_build_only_exposes_probe_not_production_feeds(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = build(output)
            actual = (output / FEED).read_bytes()
            self.assertEqual(report["sha256"], hashlib.sha256(actual).hexdigest())
            self.assertEqual(report["device_acceptance"], "failed")
            for name in ("calendar.ics", "holidays.ics", "festivals.ics", "solar_terms.ics"):
                self.assertFalse((output / name).exists())
            self.assertEqual(json.loads((output / "status.json").read_text())["event_count"], 4)
            self.assertEqual(report["candidate"]["sha256"], hashlib.sha256((output / CANDIDATE_FEED).read_bytes()).hexdigest())
            self.assertEqual(report["candidate"]["device_acceptance"], "failed")

    def test_reject_build_into_source(self):
        with self.assertRaises(ValueError):
            build(ROOT / "dist")


class GroupedCandidateTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()
        self.raw = render_grouped_candidate(self.probe)
        self.cal = Calendar.from_ical(self.raw)
        self.events = self.cal.walk("VEVENT")

    def test_parser_metadata_and_diagnostic_legacy_language(self):
        self.assertEqual(len(self.events), 4)
        self.assertFalse(self.cal.errors)
        self.assertNotIn("X-WR-TIMEZONE", self.cal)
        self.assertEqual(str(self.cal["X-APPLE-LANGUAGE"]), "zh")
        self.assertEqual(str(self.cal["X-APPLE-REGION"]), "CN")
        for event in self.events:
            self.assertFalse(event.errors)
            self.assertEqual(event["SUMMARY"].params["LANGUAGE"], "zh_CN")
            self.assertEqual(event["CATEGORIES"].to_ical().decode("utf-8"), "節慶")
            self.assertEqual(event["DTSTAMP"].dt.utcoffset(), timedelta(0))

    def test_government_interval_and_implicit_single_day(self):
        by_start = {e.decoded("DTSTART"): e for e in self.events}
        holiday = by_start[date(2026, 10, 1)]
        self.assertEqual(holiday.decoded("DTEND"), date(2026, 10, 8))
        self.assertEqual(str(holiday["X-APPLE-SPECIAL-DAY"]), "WORK-HOLIDAY")
        workday = by_start[date(2026, 10, 10)]
        self.assertEqual(str(workday["X-APPLE-SPECIAL-DAY"]), "ALTERNATE-WORKDAY")
        for day in (9, 10, 11):
            self.assertNotIn("DTEND", by_start[date(2026, 10, day)])
            self.assertNotIn("DURATION", by_start[date(2026, 10, day)])
        for day in (9, 11):
            self.assertNotIn("X-APPLE-SPECIAL-DAY", by_start[date(2026, 10, day)])

    def test_shared_holiday_identity_with_distinct_event_uids(self):
        marked = [e for e in self.events if "X-APPLE-SPECIAL-DAY" in e]
        self.assertEqual(len({str(e["X-APPLE-UNIVERSAL-ID"]) for e in marked}), 1)
        own_ids = {str(e["UID"]) for e in self.events}
        self.assertEqual(len(own_ids), 4)
        baseline_ids = {str(e["UID"]) for e in Calendar.from_ical(render_calendar(self.probe)).walk("VEVENT")}
        self.assertFalse(own_ids & baseline_ids)
        group = str(marked[0]["X-APPLE-UNIVERSAL-ID"])
        self.assertTrue(all(str(e["X-APPLE-UNIVERSAL-ID"]) != group for e in self.events if "X-APPLE-SPECIAL-DAY" not in e))

    def test_baseline_bytes_frozen_and_candidate_deterministic(self):
        baseline_hash = hashlib.sha256(render_calendar(self.probe)).hexdigest()
        self.assertEqual(baseline_hash, "7154a2afb5acde114785d44329c248179813783167e35d437f031b613643eb14")
        self.assertEqual(self.raw, render_grouped_candidate(self.probe))
        self.assertNotIn(b"\n", self.raw.replace(b"\r\n", b""))
        for line in self.raw.split(b"\r\n"):
            self.assertLessEqual(len(line), 75)
            line.decode("utf-8")


if __name__ == "__main__":
    unittest.main()
