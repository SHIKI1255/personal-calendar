# Accepted revision — 2026-10-06

User cancelled self-hosted work/rest schedules, native badges and the acceptance
gate after r1 and B1 failed on the reported device. Apple schedules are a separate
user subscription, never a production upstream.

Three feeds: calendar.ics (union), festivals.ics, solar_terms.ics. Full self-hosted
content remains where Apple overlaps. Combined or separate subscriptions are
selectable at the public page. No holidays.ics. Preserve the old probe URLs
byte-for-byte as frozen historical evidence, with unsubscribe notice.

Inventory: data/festivals.json. Python 3.12, lunar_python 1.4.8 (MIT) for offline
lunar and solar-term algorithms only. Fixed/weekday/Oudin Easter/relative rules
belong to this repository. TOML config uses stdlib; JSON definitions avoid another
parser dependency. No calendar APIs, database, daemon, AI or schedule scraper.

Beijing year minus three through plus three. Evaluate adjacent lunar years then
filter; no leap-month repeats; eve is next spring festival minus one day. Select
the current-year winter solstice from the library's multi-year table. All-day,
transparent, no alarm/emoji. Merge Qingming only in the combined feed; preserve
other same-day events and complete category feeds.

UID = canonical ID plus owning Gregorian/lunar year. Feed-specific revisions avoid
coupling distinct summaries/categories. Persist creation/modification/sequence
and content hash, archive out-of-window identities. Persisted state and unchanged
content yield identical bytes. Exclusive DATE end, UTF-8 octet folding, CRLF.

Daily lightweight gate at 06:17 Beijing; weekly Monday, first successful monthly/
yearly cycle, previous-failure retry and explicit requests build fully. Tests
precede staging; deploy one complete Pages artifact only if manifest changes.
Verify remote manifest/files/MIME before recording health or marking last-good.
Read-only PR jobs; main-only write jobs; SHA-pinned Actions; no PAT. Monthly real
health commits; ordinary weekly success does not rewrite calendars.

Deduplicate maintenance issues, close on recovery. Last-good artifacts retained
90 days support explicit whole-version restore. Rollback preserves revision
history; current source resumes on the next normal run. Git history provides
longer-term recovery.

Independent HKO snapshots validate every day in 2023–2029 plus all 168 solar terms.
New rollover years beyond this reference set have algorithm/structural checks;
do not label them HKO-verified. Dependency/algorithm changes rerun all fixtures.
No promise of unlimited astronomical precision or perpetual GitHub scheduling.

Actual iPhone regular all-day display, combined/category modes and same-URL
refresh remain separate device acceptance. Never infer them from CI. No badge gate.
