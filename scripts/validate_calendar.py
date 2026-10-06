"""Independent ICS checks, used before writing any candidate publication."""
from datetime import date, timedelta
from icalendar import Calendar


def validate_ics(raw, expected=None):
    if not raw.endswith(b"\r\n") or b"\n" in raw.replace(b"\r\n", b""):
        raise ValueError("ICS must use CRLF")
    for line in raw.split(b"\r\n"):
        if len(line) > 75:
            raise ValueError("ICS physical line exceeds 75 octets")
        line.decode("utf-8")
    calendar = Calendar.from_ical(raw)
    if calendar.errors:
        raise ValueError(str(calendar.errors))
    events = calendar.walk("VEVENT")
    seen = set()
    for event in events:
        if event.errors:
            raise ValueError(str(event.errors))
        uid = str(event["UID"])
        if uid in seen:
            raise ValueError("Duplicate UID")
        seen.add(uid)
        start, end = event.decoded("DTSTART"), event.decoded("DTEND")
        if type(start) is not date or end != start + timedelta(days=1):
            raise ValueError("Expected one all-day event with exclusive end")
        if str(event["TRANSP"]) != "TRANSPARENT" or event.walk("VALARM") or "X-APPLE-SPECIAL-DAY" in event:
            raise ValueError("Unexpected busy time, alarm or work/rest flag")
        if event["DTSTAMP"].dt.utcoffset() != timedelta(0):
            raise ValueError("DTSTAMP must be UTC")
    if expected is not None:
        actual = {str(e["UID"]): (e.decoded("DTSTART"), str(e["SUMMARY"])) for e in events}
        if actual != {e.uid: (e.start, e.title) for e in expected}:
            raise ValueError("Rendered events differ from generated events")
    return len(events)
