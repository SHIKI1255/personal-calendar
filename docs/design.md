# Accepted product specification

Status: design approved; implementation gated by native Apple badge acceptance.
This document describes future work, not completed features.

## Acceptance gate

Target: iPhone 18 Pro Max, iOS 27, Hong Kong region. Self-hosted feed must show
native work/rest badges without relying on other calendars. Normal controls must
have no badge. A same-URL r1-to-r2 refresh must keep UIDs and avoid duplicates.
No region changes or text-only substitute. Failure pauses full implementation.

## Product

Four stable public endpoints: calendar.ics, holidays.ics, festivals.ics,
solar_terms.ics. One combined subscription OR any combination of category feeds;
category feeds remain complete and independently selectable. Combined feed merges
the same festival and official day status, Qingming festival/solar term, and Easter
duplicates. Distinct same-day festivals remain distinct. Both combined and holiday
feeds need native badges. Do not subscribe to combined plus its categories.

Asia/Shanghai; three past years + current + three future years, full Gregorian
years (2023–2029 in 2026; 2024–2030 in 2027). Roll on first successful annual run,
retain archived source data. Future work/rest schedules must never be guessed.
All-day, transparent, no alarms, Chinese titles, emoji off by default.

## Sources and calculations

Official State Council notices first; government reposts and corrections as
fallback. Verify title, issuing body, year, document number, complete paragraphs
and dates. Persist annual JSON plus source body, URL, publication/retrieval time
and hash. Cover already-announced years from 2023 and adjacent-year spillovers.
Zero make-up workdays can be valid; unknown, missing, inaccessible and invalid
are separate states. Network failure is not proof of absence. Reject conflicts,
omitted dates and unexplained paragraphs; preserve last confirmed publication.
No third-party ICS, private calendar API, Apple date data or borrowed holiday table.

Use Python 3.12. Fixed/nth-weekday/Gregorian Easter algorithms in this project.
Use lunar_python==1.4.8 only for offline lunar/solar-term algorithms with MIT notice,
not its built-in festival list or holiday schedules. Initially publish solar-term
dates only. Independent date fixtures from Hong Kong Observatory, not the algorithm
under test. Lock dependencies; no database, daemon or online AI parser.

Traditional: Spring Festival, Lantern Festival, Qingming, Dragon Boat, Qixi,
Ghost Festival, Mid-Autumn, Double Ninth, Laba, northern/southern Little New Year,
Chinese New Year's Eve (day before next Spring Festival). No leap-month repeats.
Common: New Year, Valentine's, Women's Day, April Fools', Easter, Mother's Day
(May second Sunday), Father's Day (June third Sunday), Halloween (Oct 31), US
Thanksgiving (November fourth Thursday), Black Friday, Christmas Eve, Christmas,
New Year's Eve. Add Labor Day and National Day festival identity for merging with
official holidays. Holy Week: Palm Sunday, Maundy Thursday, Good Friday, Holy
Saturday, Easter Sunday; Easter Monday optional/off. All 24 solar terms.

YAML configuration: timezone, past=3/future=3, categories, Holy Week, regional
options, emoji=false, Apple extensions. Data-driven festival definitions. CLI:
update official data (optional explicit URL/year), offline build, full validation.
Stable canonical IDs; persistent timestamps/sequence only change with event
content. UTF-8, CRLF, octet folding, escaping, exclusive DATE end, categories.

## Automation after acceptance

Daily lightweight wake at 06:17 Beijing. Actual fetch weekly Monday in Jan–Sep,
daily in Oct–Dec, daily while current-year schedule is missing, and next-day retry
after fetch/deploy failures. Manual dispatch always available. Annual rollover and
monthly truthful health record on first run. Up to three network attempts with
timeouts/backoff. No official fetch on ordinary skip days.

Stage candidate → validate → generate four feeds → test → commit real changes →
explicit Pages deploy → verify live bytes/MIME/status. Failed validation preserves
previous confirmed data/site. Atomic four-feed deployment and rollback entrypoint.
No-change ICS has no commit; separate monthly health commit helps avoid GitHub's
60-day inactivity disablement. Deduplicated issue on failure, close on recovery,
no routine success messages. No external uptime monitor; annual manual health
check remains needed. Client refresh latency is not controlled by the server.
Minimum job permissions, actions pinned by SHA, no long-lived PAT. Dependabot
monthly grouped PRs; no automatic dependency/algorithm/workflow merges.

## Remaining validation and delivery

Seven-year coverage/rollover/leap days; all fixed/nth-weekday/Easter offsets; lunar
festivals and leap-month exclusions; exactly 24 solar terms per year; 2023–2029
HKO comparisons; government historical/cross-year/merged/zero-workday/correction
fixtures; independent ICS parser, unique UID, UTF-8 and end-date checks; unchanged
build identity; network/parser/test/deployment failure and issue deduplication;
combined deduplication and category completeness; both actual Apple subscription
modes and native badges; public HTTPS MIME/hash/refresh checks. Record untested
clients explicitly. Deliver repository, real URLs, subscription/switching guide,
coverage, results, actual device evidence and limitations.
