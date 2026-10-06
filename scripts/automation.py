"""Bounded GitHub/Pages operations; no government or Apple calendar fetching."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REPO = "SHIKI1255/personal-calendar"
BASE = "https://shiki1255.github.io/personal-calendar/"
MARKER = "<!-- personal-calendar:maintenance-failure:v1 -->"
ZONE = ZoneInfo("Asia/Shanghai")


def gh_api(endpoint, method="GET", payload=None):
    command = ["gh", "api", endpoint, "--method", method]
    if payload is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                            capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def output(key, value):
    print(f"{key}={value}")
    if os.getenv("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
            stream.write(f"{key}={value}\n")


def gate_due(now, event, health, previous_failed=False):
    local = now.astimezone(ZONE)
    reasons = []
    if event != "schedule":
        reasons.append("explicit-trigger")
    if previous_failed:
        reasons.append("retry-failure")
    if health.get("year") != local.year:
        reasons.append("year-rollover")
    if health.get("month") != local.strftime("%Y-%m"):
        reasons.append("monthly-health")
    if local.weekday() == 0:
        reasons.append("weekly-check")
    return bool(reasons), reasons


def gate():
    health_file = ROOT / "state/health.json"
    health = json.loads(health_file.read_text()) if health_file.exists() else {}
    runs = gh_api(f"repos/{REPO}/actions/workflows/update-calendar.yml/runs?branch=main&per_page=30")["workflow_runs"]
    completed = [r for r in runs if str(r['id']) != os.getenv('GITHUB_RUN_ID') and r['status'] == 'completed' and r['event'] != 'pull_request']
    previous_failed = bool(completed and completed[0]['conclusion'] not in ('success','skipped'))
    due, reasons = gate_due(datetime.now(timezone.utc), os.getenv("GITHUB_EVENT_NAME", "workflow_dispatch"), health, previous_failed)
    output("due", str(due).lower())
    print("Reasons: " + ", ".join(reasons or ["no maintenance due"]))


def get_public(path):
    # Paths come only from our candidate manifest, not arbitrary remote input.
    if path.startswith('/') or '..' in path.split('/') or ':' in path:
        raise ValueError("Unsafe publication path")
    request = Request(BASE + path, headers={"User-Agent": "personal-calendar-health/1", "Cache-Control": "no-cache"})
    with urlopen(request, timeout=30) as response:
        return response.read(), response.headers.get_content_type()


def changed(site):
    desired = json.loads((site / "status.json").read_text(encoding="utf-8"))
    try:
        raw, _ = get_public("status.json")
        current = json.loads(raw)
    except HTTPError as exc:
        if exc.code != 404:
            raise
        current = {}
    output("changed", str(current != desired).lower())


def verify_once(site, fetch=get_public):
    expected = json.loads((site / "status.json").read_text(encoding="utf-8"))
    raw, _ = fetch("status.json")
    if json.loads(raw) != expected:
        raise ValueError("Public status manifest differs from candidate")
    for path, checksum in expected["files"].items():
        raw, mime = fetch(path)
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError("Public content hash mismatch: " + path)
        if path.endswith('.ics') and mime != 'text/calendar':
            raise ValueError("Unexpected calendar MIME: " + mime)
    return expected


def verify(site):
    for attempt in range(3):
        try:
            report = verify_once(site)
            print("Public content, MIME and version verified: " + report['release'])
            return report
        except Exception:
            if attempt == 2:
                raise
            time.sleep(20 * (attempt + 1))


def open_failure_issues(api=gh_api):
    result, page = [], 1
    while True:
        rows = api(f"repos/{REPO}/issues?state=open&per_page=100&page={page}")
        result.extend(r for r in rows if 'pull_request' not in r and MARKER in (r.get('body') or '')
                      and r.get('user', {}).get('login') == 'github-actions[bot]')
        if len(rows) < 100:
            return result
        page += 1


def reconcile_issue(failed, run_url, api=gh_api):
    issues = open_failure_issues(api)
    if failed:
        body = MARKER + "\n日历维护失败；上一成功版本可从 Actions 的 last-good-site 恢复。\n\n运行记录：" + run_url
        if issues:
            api(f"repos/{REPO}/issues/{issues[0]['number']}", "PATCH", {"body": body})
        else:
            api(f"repos/{REPO}/issues", "POST", {"title": "Calendar maintenance requires review", "body": body})
    else:
        for issue in issues:
            api(f"repos/{REPO}/issues/{issue['number']}", "PATCH", {"state": "closed", "state_reason": "completed"})


def record_success(site, candidate_state, rollback=False):
    report = json.loads((site / 'status.json').read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZONE)
    iso = local.isocalendar()
    state = ROOT / 'state'
    state.mkdir(exist_ok=True)
    health = {'year': local.year, 'month': local.strftime('%Y-%m'), 'week': f'{iso.year}-W{iso.week:02}',
              'last_checked': now.isoformat(), 'release': report['release'],
              'years': report['years'], 'run_url': os.getenv('RUN_URL','local'), 'rollback': rollback}
    # Only called after live verification; monthly file is immutable after first success.
    monthly = state / 'health' / (local.strftime('%Y-%m') + '.json')
    monthly.parent.mkdir(exist_ok=True)
    first_month_check = not monthly.exists()
    if first_month_check:
        monthly.write_text(json.dumps(health,indent=2)+'\n',encoding='utf-8')
    previous_file = state/'health.json'
    previous = json.loads(previous_file.read_text()) if previous_file.exists() else {}
    if first_month_check or previous.get('release') != report['release'] or rollback:
        previous_file.write_text(json.dumps(health,indent=2)+'\n',encoding='utf-8')
    # Rollback must not rewind event revision history. Future rebuilds retain latest identities.
    if not rollback:
        candidate = json.loads(candidate_state.read_text(encoding='utf-8'))
        (state/'events.json').write_text(json.dumps(candidate,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def restore(run_id, directory):
    if not run_id.isdecimal():
        raise ValueError('Rollback run ID must be numeric')
    run = gh_api(f'repos/{REPO}/actions/runs/{run_id}')
    if run['conclusion'] != 'success' or run['head_branch'] != 'main' or run['event'] == 'pull_request':
        raise ValueError('Only a successful main publication can be restored')
    subprocess.run(['gh','run','download',run_id,'--repo',REPO,'--name','last-good-site','--dir',str(directory)],check=True)
    report=json.loads((directory/'site/status.json').read_text(encoding='utf-8'))
    for path,checksum in report['files'].items():
        target=(directory/'site'/path).resolve()
        if (directory/'site').resolve() not in target.parents or hashlib.sha256(target.read_bytes()).hexdigest()!=checksum:
            raise ValueError('Invalid rollback artifact')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['gate','changed','verify','success','failure','close-issue','restore'])
    parser.add_argument('--site',type=Path)
    parser.add_argument('--candidate-state',type=Path)
    parser.add_argument('--rollback',action='store_true')
    parser.add_argument('--run-id')
    parser.add_argument('--directory',type=Path)
    args=parser.parse_args()
    if args.command=='gate': gate()
    elif args.command=='changed': changed(args.site)
    elif args.command=='verify': verify(args.site)
    elif args.command=='success': record_success(args.site,args.candidate_state,args.rollback)
    elif args.command=='restore': restore(args.run_id,args.directory)
    else: reconcile_issue(args.command=='failure',os.getenv('RUN_URL','see Actions'))
