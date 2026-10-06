# Third-party notices

## lunar_python 1.4.8

Source: https://github.com/6tail/lunar-python
Package: https://pypi.org/project/lunar_python/1.4.8/
Only offline lunar conversion and solar-term calculations are used. Predefined
festival lists and holiday/workday tables are not used.

MIT License

Copyright (c) 2020 6tail

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Independent reference data

Hong Kong Observatory, Gregorian-Lunar Calendar Conversion Tables:
https://www.hko.gov.hk/tc/gts/time/conversion.htm

Annual snapshots retain source URLs, retrieval times and SHA-256 in
tests/fixtures/hko/sources.json. HKO data is reference material, not claimed under
the repository's MIT code license and not used as a production generation upstream.

The archived government notice used only for the cancelled badge experiment retains
provenance in data/compatibility. No government data ownership is claimed. No Apple
ICS content is copied into this repository.

Easter reference: US Naval Observatory, The Date of Easter,
https://aa.usno.navy.mil/faq/easter (Oudin algorithm, explanatory integer steps).

Independent test parser: icalendar (BSD-2-Clause); typing-extensions (PSF-2.0);
python-dateutil (Apache-2.0/BSD); six (MIT); tzdata (Apache-2.0 package, IANA data public domain). Packages are installed
separately under their own licenses, locked in the requirements files.
