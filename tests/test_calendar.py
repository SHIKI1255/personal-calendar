import copy
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from calendar_core import (ROOT, TERMS, load_inputs, year_window, nth_weekday, easter,
                           lunar_date, solar_terms, make_feeds, render_feeds, rule_date)
from calendar_cli import build
from validate_calendar import validate_ics
from hko_reference import read_reference
from lunar_python import Solar
from icalendar import Calendar

NOW = datetime(2026, 10, 6, 8, tzinfo=timezone.utc)


class CalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.rules = load_inputs()
        # Algorithm regression tests use a complete reference configuration. User
        # display preferences must not make the independent date suite fail.
        cls.config.update(past_years=3, future_years=3)
        cls.config['categories'] = {key: True for key in cls.config['categories']}
        cls.config['festivals'].update(little_new_year='both', easter_monday=False, disabled_ids=[])
        cls.config['solar_terms']['disabled_ids'] = []
        cls.feeds, cls.window = make_feeds(cls.config, cls.rules, NOW)
        cls.raw, cls.state = render_feeds(cls.feeds, {}, NOW)

    def test_beijing_rollover_and_seven_full_years(self):
        self.assertEqual(self.window, (2023, 2029))
        self.assertEqual(year_window(datetime(2026,12,31,15,59,tzinfo=timezone.utc), self.config), (2023,2029))
        self.assertEqual(year_window(datetime(2026,12,31,16,tzinfo=timezone.utc), self.config), (2024,2030))
        with self.assertRaises(ValueError):
            year_window(datetime(2026,1,1), self.config)
        for events in self.feeds.values():
            self.assertTrue(all(date(2023,1,1) <= e.start < date(2030,1,1) for e in events))

    def test_hko_every_lunar_day_and_all_168_solar_terms(self):
        rows, terms = read_reference()
        checked = 0
        for day, expected in rows.items():
            if 2023 <= day.year <= 2029:
                actual = Solar.fromYmd(day.year, day.month, day.day).getLunar()
                self.assertEqual((actual.getYear(), actual.getMonth(), actual.getDay()), expected, day.isoformat())
                checked += 1
        self.assertEqual(checked, 2557)
        for year in range(2023,2030):
            calculated = {d: TERMS[k] for k,d in solar_terms(year).items()}
            self.assertEqual(calculated, {d:t for d,t in terms.items() if d.year == year})
            self.assertEqual(len(calculated), 24)

    def test_all_generated_lunar_festivals_match_independent_hko_rows(self):
        rows, _ = read_reference()
        rules = {r['id']:r for r in self.rules}
        for event in self.feeds['festivals.ics']:
            identity, year = event.identity.rsplit('-',1)
            rule = rules[identity]
            if rule['type'] == 'lunar':
                self.assertEqual(rows[event.start], (int(year[1:]), rule['month'], rule['day']))
            elif rule['type'] == 'lunar_eve':
                self.assertEqual(rows[event.start + timedelta(days=1)][1:], (1,1))

    def test_nth_weekday_and_relative_black_friday(self):
        self.assertEqual(nth_weekday(2026,5,6,2), date(2026,5,10))
        self.assertEqual(nth_weekday(2027,6,6,3), date(2027,6,20))
        self.assertEqual(nth_weekday(2028,11,3,4), date(2028,11,23))
        with self.assertRaises(ValueError):
            nth_weekday(2026,2,0,5)
        for year in range(2023,2030):
            entries = {e.identity:e for e in self.feeds['festivals.ics']}
            self.assertEqual(entries[f'black-friday-g{year}'].start, entries[f'thanksgiving-us-g{year}'].start + timedelta(days=1))

    def test_easter_usno_published_examples_and_century_boundaries(self):
        # USNO published examples (1954, 1962, 2010); independent dateutil computus
        # checks the broader Gregorian range, including non-leap century 2100.
        for year, expected in {1954:'1954-04-18',1962:'1962-04-22',2010:'2010-04-04',2024:'2024-03-31',2026:'2026-04-05'}.items():
            self.assertEqual(easter(year), date.fromisoformat(expected))
        from dateutil.easter import easter as independent
        for year in range(1901,2201):
            self.assertEqual(easter(year), independent(year), year)

    def test_holy_week_and_coincident_distinct_festivals(self):
        entries = {e.identity:e for e in self.feeds['calendar.ics']}
        for identity, offset in {'palm-sunday':-7,'maundy-thursday':-3,'good-friday':-2,'holy-saturday':-1,'easter':0}.items():
            self.assertEqual(entries[identity+'-g2026'].start, easter(2026)+timedelta(days=offset))
        self.assertEqual(entries['qingming-g2026'].start, entries['easter-g2026'].start)
        self.assertNotEqual(entries['qingming-g2026'].uid, entries['easter-g2026'].uid)

    def test_lunar_eve_short_month_leap_month_and_boundary_laba(self):
        events = self.feeds['festivals.ics']
        self.assertIn(date(2026,2,16), [e.start for e in events if e.title == '除夕'])
        self.assertIn(date(2024,1,18), [e.start for e in events if e.title == '腊八节'])
        self.assertEqual(lunar_date(2026,1,1), date(2026,2,17))
        with self.assertRaises(ValueError):
            lunar_date(2025,-6,1)
        self.assertEqual(len([e for e in events if e.identity == 'qixi-l2025']), 1)

    def test_combined_dedup_and_category_completeness(self):
        self.assertEqual(len(self.feeds['solar_terms.ics']), 168)
        self.assertEqual(len(self.feeds['calendar.ics']), len(self.feeds['festivals.ics'])+168-7)
        for name, events in self.feeds.items():
            self.assertEqual(len([e for e in events if e.identity.startswith('qingming-')]), 7)
            self.assertEqual(len({e.uid for e in events}),len(events))
        self.assertFalse(any(e.title == '复活节星期一' for e in self.feeds['festivals.ics']))

    def test_configuration_and_disabled_base_still_computes_relative_day(self):
        config = copy.deepcopy(self.config)
        config['festivals'].update(little_new_year='north', easter_monday=True, disabled_ids=['thanksgiving-us'])
        config['solar_terms']['disabled_ids'] = ['qingming']
        feeds, _ = make_feeds(config, self.rules, NOW)
        titles = {e.title for e in feeds['festivals.ics']}
        self.assertNotIn('小年（南方）', titles)
        self.assertNotIn('感恩节', titles)
        self.assertIn('黑色星期五', titles)
        self.assertIn('复活节星期一', titles)
        self.assertEqual(len(feeds['solar_terms.ics']),161)
        config['categories']['solar_terms'] = False
        self.assertEqual(make_feeds(config, self.rules, NOW)[0]['solar_terms.ics'], [])

    def test_leap_year_and_relative_cycle_rejection(self):
        self.assertEqual(rule_date({'id':'test','type':'fixed','month':2,'day':29},2024,{}),date(2024,2,29))
        with self.assertRaises(ValueError):
            rule_date({'id':'test','type':'fixed','month':2,'day':29},2025,{})
        cyclic = {'id':'test','type':'relative','base':'test','offset':1}
        with self.assertRaises(ValueError):
            rule_date(cyclic,2026,{'test':cyclic})

    def test_ics_independent_parser_and_no_work_rest(self):
        for name, raw in self.raw.items():
            self.assertEqual(validate_ics(raw,self.feeds[name]),len(self.feeds[name]))
            self.assertNotIn(b'X-APPLE-SPECIAL-DAY',raw)

    def test_unchanged_bytes_despite_run_time_and_state_not_mutated(self):
        old = copy.deepcopy(self.state)
        raw, state = render_feeds(self.feeds,self.state,NOW+timedelta(days=100))
        self.assertEqual(self.raw,raw)
        self.assertEqual(old,state)
        self.assertEqual(old,self.state)

    def test_changed_date_or_title_keeps_uid_and_increases_revision(self):
        feeds = copy.deepcopy(self.feeds)
        previous = feeds['festivals.ics'][0]
        feeds['festivals.ics'][0] = replace(previous,title='修订标题',start=previous.start+timedelta(days=1))
        raw,state=render_feeds(feeds,self.state,NOW+timedelta(days=1))
        a=Calendar.from_ical(self.raw['festivals.ics']).walk('VEVENT')[0]
        b=Calendar.from_ical(raw['festivals.ics']).walk('VEVENT')[0]
        self.assertEqual(a['UID'],b['UID'])
        self.assertEqual(b['SEQUENCE'],a['SEQUENCE']+1)
        self.assertEqual(a['CREATED'],b['CREATED'])
        self.assertNotEqual(a['LAST-MODIFIED'],b['LAST-MODIFIED'])

    def test_archived_revision_state_survives_rollover(self):
        future,_=make_feeds(self.config,self.rules,NOW.replace(year=2027))
        _,state=render_feeds(future,self.state,NOW.replace(year=2027))
        self.assertTrue(set(self.state['events']) <= set(state['events']))

    def test_candidate_validation_failure_preserves_existing_site_and_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('calendar_cli.validate_ics',side_effect=ValueError('test failure')):
                with self.assertRaises(ValueError):
                    build(root/'site',root/'state.json',NOW)
            self.assertFalse((root/'site').exists())
            self.assertFalse((root/'state.json').exists())
            (root/'site').mkdir()
            (root/'site/keep').write_text('last good')
            with self.assertRaises(ValueError):
                build(root/'site',root/'state.json',NOW)
            self.assertEqual((root/'site/keep').read_text(),'last good')

    def test_full_candidate_has_three_feeds_and_frozen_probes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            report=build(root/'site',root/'state.json',NOW)
            self.assertEqual(report['years'],list(year_window(NOW,load_inputs()[0])))
            self.assertFalse((root/'site/holidays.ics').exists())
            self.assertTrue((root/'site/compatibility/apple-badges.ics').is_file())
            self.assertEqual(set(report['event_counts']),set(self.feeds))
            self.assertNotIn('.nojekyll',report['files'])

    def test_custom_display_configuration_builds_and_unknown_ids_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            config=root/'config.toml'
            config.write_text('''timezone="Asia/Shanghai"
past_years=0
future_years=0
[categories]
traditional=false
common=false
holy_week=false
solar_terms=true
[festivals]
little_new_year="none"
easter_monday=false
disabled_ids=[]
[solar_terms]
disabled_ids=["qingming"]
''',encoding='utf-8')
            report=build(root/'site',root/'state.json',NOW,config_path=config)
            self.assertEqual(report['years'],[2026,2026])
            self.assertEqual(report['event_counts'],{'calendar.ics':23,'festivals.ics':0,'solar_terms.ics':23})
            config.write_text(config.read_text().replace('"qingming"','"unknown-term"'))
            with self.assertRaises(ValueError):load_inputs(config)


if __name__ == '__main__':
    unittest.main()
