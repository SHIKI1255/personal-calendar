# personal-calendar

Use PowerShell 7 for local shell commands. Read local_task_preflight_profile.yaml
and manifest.json before changes. This is SHIKI1255/personal-calendar, branch main.

Current release is an Apple badge compatibility probe. Full calendar development
is gated on the user's real-device acceptance, including a same-URL refresh test.
Do not mark the gate passed based on ICS parsing, screenshots from others, or CI.
Do not change the device region or substitute title text for native badges.

Only official government announcements supply holiday/workday dates. Algorithm
libraries are permitted; third-party calendars and personal APIs are not upstreams.
Retain provenance, fixtures, stable UIDs and confirmed data on every failure.

Run scripts/preflight.py and tests before publication. Stage explicit paths only.
Preserve unrelated changes. Commit/push/deploy require covering user authority.
Generated local output belongs outside this source tree, under the configured
workbench partition. CI uses RUNNER_TEMP. Never run implicit cleanup or modify
other repositories, Codex state, credentials or the central governance registry.

Local controls are self-contained. The central governance context was consulted
during onboarding; central registration is not claimed or required at runtime.
