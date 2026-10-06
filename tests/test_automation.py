from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import automation as a


class AutomationTests(unittest.TestCase):
    def test_weekly_monthly_rollover_failure_and_manual_gate(self):
        now=datetime(2026,10,6,tzinfo=timezone.utc)
        health={'year':2026,'month':'2026-10','week':'2026-W41'}
        self.assertFalse(a.gate_due(now,'schedule',health)[0])
        self.assertTrue(a.gate_due(now,'schedule',health,True)[0])
        self.assertTrue(a.gate_due(now,'workflow_dispatch',health)[0])
        for key in ('year','month'):
            stale=dict(health);stale.pop(key)
            self.assertTrue(a.gate_due(now,'schedule',stale)[0])
        self.assertTrue(a.gate_due(datetime(2026,12,31,16,tzinfo=timezone.utc),'schedule',health)[0])

    def test_deduplicate_issue_and_close_on_recovery(self):
        calls=[]
        existing=[]
        def api(endpoint,method='GET',payload=None):
            calls.append((endpoint,method,payload))
            if method=='GET':return existing.copy()
            if method=='POST':existing.append({'number':42,'body':payload['body'],'user':{'login':'github-actions[bot]'}})
        a.reconcile_issue(True,'first',api)
        a.reconcile_issue(True,'second',api)
        a.reconcile_issue(False,'recovered',api)
        self.assertEqual(sum(c[1]=='POST' for c in calls),1)
        self.assertEqual(calls[-1][2],{'state':'closed','state_reason':'completed'})

    def test_public_hash_mime_and_status_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            site=Path(folder)
            raw=b'calendar bytes'
            import hashlib
            report={'release':'test','files':{'calendar.ics':hashlib.sha256(raw).hexdigest()}}
            (site/'status.json').write_text(json.dumps(report))
            def fetch(path):
                return (json.dumps(report).encode(),'application/json') if path=='status.json' else (raw,'text/calendar')
            self.assertEqual(a.verify_once(site,fetch),report)
            for wrong,mime in [(b'wrong','text/calendar'),(raw,'text/plain')]:
                def bad(path):
                    return fetch(path) if path=='status.json' else (wrong,mime)
                with self.assertRaises(ValueError):a.verify_once(site,bad)
            with self.assertRaises(ValueError):
                a.verify_once(site,lambda path:(b'{}','application/json'))

    def test_failed_publication_never_records_success_and_retry_is_bounded(self):
        with patch('automation.verify_once',side_effect=ValueError('mismatch')) as verify, patch('automation.time.sleep') as sleep:
            with self.assertRaises(ValueError):a.verify(Path('unused'))
            self.assertEqual(verify.call_count,3)
            self.assertEqual(sleep.call_count,2)

    def test_monthly_record_immutable_and_rollback_preserves_revisions(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);site=root/'site';site.mkdir()
            (site/'status.json').write_text(json.dumps({'release':'one','years':[2023,2029]}))
            candidate=root/'candidate.json';candidate.write_text('{"events":{"test":{}}}')
            with patch('automation.ROOT',root):
                a.record_success(site,candidate)
                monthly=next((root/'state/health').glob('*.json'));before=monthly.read_bytes()
                events=(root/'state/events.json').read_bytes()
                candidate.write_text('{}')
                a.record_success(site,candidate,rollback=True)
                self.assertEqual(monthly.read_bytes(),before)
                self.assertEqual((root/'state/events.json').read_bytes(),events)

    def test_untrusted_restore_run_rejected_before_download(self):
        with patch('automation.gh_api',return_value={'conclusion':'failure','head_branch':'main','event':'push'}), patch('automation.subprocess.run') as run:
            with self.assertRaises(ValueError):a.restore('123',Path('unused'))
            run.assert_not_called()
        with self.assertRaises(ValueError):a.restore('../bad',Path('unused'))
