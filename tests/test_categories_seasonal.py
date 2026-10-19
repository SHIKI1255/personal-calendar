import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from calendar_core import (ROOT, CATEGORY_REGISTRY, FESTIVAL_CATEGORIES, SEASONAL_RULES,
                           load_inputs, make_feeds, render_feeds, catalog_entries, sanfu)
from calendar_cli import build, render_index
from catalog import search_catalog
from validate_calendar import validate_ics
from hko_reference import read_reference

NOW = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)


class CategorySeasonalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.rules = load_inputs()
        cls.config.update(past_years=3, future_years=3)
        cls.config['categories'] = {key: True for key in cls.config['categories']}
        cls.config['festivals'].update(little_new_year='both', easter_monday=True, disabled_ids=[])
        cls.config['solar_terms']['disabled_ids'] = []
        cls.config['seasonal'].update(sanfu=True, shujiu=True, disabled_ids=[])
        cls.feeds, _ = make_feeds(cls.config, cls.rules, NOW)
        cls.raw, cls.state = render_feeds(cls.feeds, {}, NOW)

    def test_inventory_membership_and_ten_complete_feeds(self):
        self.assertEqual(len(self.rules), 42)
        self.assertEqual(len(SEASONAL_RULES), 14)
        catalog = catalog_entries(self.config, self.rules)
        self.assertEqual([r['id'] for r in catalog if r['category'] == 'seasonal'],
                         [r['id'] for r in SEASONAL_RULES])
        self.assertEqual(len(self.feeds), 10)
        counts = {r['id']: sum(e['category'] == r['id'] for e in self.rules)
                  for r in CATEGORY_REGISTRY if r['id'] in FESTIVAL_CATEGORIES}
        self.assertEqual(counts, dict(traditional=8, folk=8, public=10, family=3, culture=5, christian=8))
        union = {e.identity: e for r in CATEGORY_REGISTRY if r['id'] in FESTIVAL_CATEGORIES
                 for e in self.feeds[r['feed']]}
        self.assertEqual(union, {e.identity: e for e in self.feeds['festivals.ics']})
        self.assertEqual(len(self.feeds['seasonal.ics']), 98)
        self.assertEqual(len(self.feeds['calendar.ics']), len(union) + 168 + 98 - 7)
        for name, raw in self.raw.items():
            self.assertEqual(validate_ics(raw, self.feeds[name]), len(self.feeds[name]))

    def test_each_category_switch_preserves_other_category_bytes(self):
        for group in CATEGORY_REGISTRY:
            with self.subTest(group=group['id']):
                config = copy.deepcopy(self.config)
                config['categories'][group['id']] = False
                feeds, _ = make_feeds(config, self.rules, NOW)
                raw, _ = render_feeds(feeds, self.state, NOW + timedelta(days=1))
                self.assertEqual(validate_ics(raw[group['feed']]), 0)
                for other in CATEGORY_REGISTRY:
                    if other != group:
                        self.assertEqual(raw[other['feed']], self.raw[other['feed']])
                removed = {e.uid for e in self.feeds[group['feed']]}
                if group['id'] in ('traditional', 'solar_terms'):
                    removed -= {e.uid for e in self.feeds[group['feed']] if e.identity.startswith('qingming-')}
                self.assertFalse(removed & {e.uid for e in feeds['calendar.ics']})
                if group['id'] in FESTIVAL_CATEGORIES:
                    self.assertFalse({e.uid for e in self.feeds[group['feed']]} & {e.uid for e in feeds['festivals.ics']})
                else:
                    self.assertEqual(raw['festivals.ics'], self.raw['festivals.ics'])

    def test_each_item_switch_removes_only_its_target(self):
        for section, identity, feed, event_id in [
                ('festivals', 'hanyi', 'folk.ics', 'hanyi-'),
                ('solar_terms', 'dongzhi', 'solar_terms.ics', 'term-dongzhi-'),
                ('seasonal', 'shujiu-3', 'seasonal.ics', 'shujiu-3-')]:
            config = copy.deepcopy(self.config)
            config[section]['disabled_ids'] = [identity]
            feeds, _ = make_feeds(config, self.rules, NOW)
            self.assertEqual(feeds[feed], [e for e in self.feeds[feed] if not e.identity.startswith(event_id)])
            for group in CATEGORY_REGISTRY:
                if group['feed'] != feed:
                    self.assertEqual(feeds[group['feed']], self.feeds[group['feed']])

    def test_dependency_visibility_and_qingming_independence(self):
        config = copy.deepcopy(self.config)
        config['festivals']['disabled_ids'] = ['thanksgiving-us', 'qingming']
        config['categories']['solar_terms'] = False
        feeds, _ = make_feeds(config, self.rules, NOW)
        self.assertEqual(feeds['seasonal.ics'], self.feeds['seasonal.ics'])
        self.assertEqual([e for e in feeds['culture.ics'] if e.identity.startswith('black-friday-')],
                         [e for e in self.feeds['culture.ics'] if e.identity.startswith('black-friday-')])
        self.assertFalse(any(e.identity.startswith('qingming-') for e in feeds['calendar.ics']))
        config['categories']['solar_terms'] = True
        feeds, _ = make_feeds(config, self.rules, NOW)
        self.assertEqual(len([e for e in feeds['calendar.ics'] if e.title == '清明']), 7)
        config['festivals']['disabled_ids'] = []
        config['solar_terms']['disabled_ids'] = ['qingming']
        feeds, _ = make_feeds(config, self.rules, NOW)
        self.assertEqual(len([e for e in feeds['calendar.ics'] if e.title == '清明节']), 7)

    def test_sanfu_against_published_samples_and_independent_day_count(self):
        reference = json.loads((ROOT / 'tests/fixtures/seasonal_reference.json').read_text())
        for row in reference['sanfu_samples']:
            calculated = sanfu(row['year'])
            for stage in ('initial', 'middle', 'final', 'end'):
                if stage in row:
                    self.assertEqual(calculated[stage], date.fromisoformat(row[stage]))
            if 'last_inclusive' in row:
                self.assertEqual(calculated['end'] - timedelta(days=1), date.fromisoformat(row['last_inclusive']))
        _, hko = read_reference()
        # Expectations use published geng anchors and integer civil-day arithmetic,
        # not lunar_python's day-stem, solar-term or sanfu implementations.
        for anchor in reference['geng_anchors']:
            origin = date.fromisoformat(anchor['date'])
            for year in range(2023, 2030):
                terms = {name: day for day, name in hko.items() if day.year == year}
                first_geng = lambda day: day + timedelta(days=(origin - day).days % 10)
                expected = dict(initial=first_geng(terms['夏至']) + timedelta(days=20),
                                middle=first_geng(terms['夏至']) + timedelta(days=30),
                                final=first_geng(terms['立秋']))
                expected['end'] = expected['final'] + timedelta(days=10)
                self.assertEqual(sanfu(year), expected)
        self.assertEqual((sanfu(2023)['initial'] - date(2023, 6, 21)).days, 20)
        self.assertEqual((sanfu(2023)['end'] - sanfu(2023)['initial']).days, 40)
        self.assertEqual((sanfu(2025)['end'] - sanfu(2025)['initial']).days, 30)

    def test_shujiu_independent_hko_solstices_cross_year_and_leap_day(self):
        _, hko = read_reference()
        solstices = {day.year: day for day, name in hko.items() if name == '冬至'}
        expected = {}
        for year in range(2022, 2030):
            for rule in SEASONAL_RULES:
                if rule['group'] == 'shujiu':
                    start = solstices[year] + timedelta(days=rule['offset'])
                    if date(2023, 1, 1) <= start < date(2030, 1, 1):
                        expected[f"{rule['id']}-g{year}"] = start
        actual = {e.identity: e.start for e in self.feeds['seasonal.ics'] if e.identity.startswith('shujiu-')}
        self.assertEqual(actual, expected)
        self.assertEqual(actual['shujiu-end-g2023'], date(2024, 3, 12))
        self.assertIn('shujiu-3-g2022', actual)
        self.assertNotIn('shujiu-3-g2029', actual)
        for year in range(2023, 2030):
            self.assertEqual(sum(e.start.year == year for e in self.feeds['seasonal.ics']), 14)

    def test_seasonal_subgroups_and_coincident_distinct_events(self):
        for group in ('sanfu', 'shujiu'):
            config = copy.deepcopy(self.config)
            config['seasonal'][group] = False
            feeds, _ = make_feeds(config, self.rules, NOW)
            self.assertEqual(feeds['seasonal.ics'], [e for e in self.feeds['seasonal.ics'] if not e.identity.startswith(group+'-')])
        combined = {e.identity: e for e in self.feeds['calendar.ics']}
        self.assertEqual(combined['term-dongzhi-g2026'].start, combined['shujiu-1-g2026'].start)
        self.assertNotEqual(combined['term-dongzhi-g2026'].uid, combined['shujiu-1-g2026'].uid)

    def test_catalog_search_effective_state_and_qualified_identity(self):
        config = copy.deepcopy(self.config)
        config['categories']['folk'] = False
        config['festivals'].update(little_new_year='north', easter_monday=False, disabled_ids=['christmas'])
        config['seasonal']['shujiu'] = False
        catalog = catalog_entries(config, self.rules)
        self.assertEqual(len(catalog), 80)
        self.assertEqual(len({r['key'] for r in catalog}), 80)
        self.assertEqual(len(search_catalog(catalog, 'folk')), 8)
        self.assertFalse(any(r['enabled'] for r in search_catalog(catalog, 'folk')))
        self.assertEqual(len(search_catalog(catalog, search='小年')), 2)
        self.assertEqual(len(search_catalog(catalog, search=' SANFU ')), 4)
        self.assertEqual(len(search_catalog(catalog, search='qingming')), 2)
        self.assertEqual(search_catalog(catalog, 'family', 'easter'), [])
        self.assertFalse(any(r['enabled'] for r in search_catalog(catalog, search='shujiu')))
        feeds, _ = make_feeds(config, self.rules, NOW)
        for row in catalog:
            prefix = row['id'] if row['section'] != 'solar_terms' or row['id'] == 'qingming' else 'term-'+row['id']
            leaf = next(g['feed'] for g in CATEGORY_REGISTRY if g['id'] == row['category'])
            self.assertEqual(row['enabled'], any(e.identity.rsplit('-', 1)[0] == prefix for e in feeds[leaf]), row['key'])
        page = render_index(config, catalog, (2023,2029), 'https://example.test')
        self.assertIn('分类已关闭 · 地址保留为空日历', page)
        self.assertIn('季节子组已关闭', page)
        self.assertNotIn('{{', page)

    def test_catalog_cli_is_searchable_json(self):
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(ROOT/'scripts/catalog.py'),
                                 '--category', 'folk', '--search', 'shangsi', '--json'],
                                capture_output=True, encoding='utf-8', check=True)
        rows = json.loads(result.stdout)
        self.assertEqual([r['name'] for r in rows], ['上巳节'])

    def test_all_disabled_and_unknown_seasonal_id_rejected(self):
        config = copy.deepcopy(self.config)
        config['categories'] = {key: False for key in config['categories']}
        feeds, _ = make_feeds(config, self.rules, NOW)
        raw, _ = render_feeds(feeds, self.state, NOW)
        self.assertEqual(len(raw), 10)
        self.assertTrue(all(validate_ics(value) == 0 for value in raw.values()))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'config.toml'
            source = (ROOT/'config.toml').read_text(encoding='utf-8')
            source = source.replace('sanfu = true', 'sanfu = "yes"')
            path.write_text(source, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'seasonal subgroup'):
                load_inputs(path)
            source = (ROOT/'config.toml').read_text(encoding='utf-8')
            start = source.index('[seasonal]')
            source = source[:start] + source[start:].replace('disabled_ids = []', 'disabled_ids = ["unknown-season"]', 1)
            path.write_text(source, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unknown disabled identity'):
                load_inputs(path)

    def test_complete_build_catalog_manifest_and_repeat_stability(self):
        raw, state = render_feeds(self.feeds, self.state, NOW + timedelta(days=2))
        self.assertEqual(raw, self.raw)
        self.assertEqual(state, self.state)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = build(root/'site', root/'events.json', NOW, state_path=root/'input-state.json')
            self.assertEqual(len(report['event_counts']), 10)
            self.assertEqual(len(report['categories']), 8)
            self.assertEqual(len(json.loads((root/'site/catalog.json').read_text(encoding='utf-8'))), 80)
            self.assertIn('catalog.js', report['files'])
            self.assertEqual(set(report['event_counts']), set(json.loads((ROOT/'manifest.json').read_text())['production_feeds']))


if __name__ == '__main__':
    unittest.main()
