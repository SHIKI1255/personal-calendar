import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_artifacts import verify


class ArtifactTests(unittest.TestCase):
    def test_roundtrip_rejects_lost_changed_or_extra_files(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = Path(folder)
            site = candidate / "site"
            site.mkdir()
            raw = "中文日历\r\n".encode("utf-8")
            report = {"release": "test", "files": {"calendar.ics": hashlib.sha256(raw).hexdigest()}}
            public = {"calendar.ics": raw, "status.json": json.dumps(report).encode()}
            for name, value in public.items():
                (site / name).write_bytes(value)
            (site / ".nojekyll").write_bytes(b"")
            (candidate / "events.json").write_text('{"events": {}}')
            scenarios = [public, {"status.json": public["status.json"]},
                         {**public, "calendar.ics": b"corrupted"}, {**public, "extra.txt": b"extra"}]
            for index, files in enumerate(scenarios):
                archive = candidate / f"{index}.tar"
                with tarfile.open(archive, "w") as output:
                    for name, value in files.items():
                        member = tarfile.TarInfo("./" + name)
                        member.size = len(value)
                        output.addfile(member, io.BytesIO(value))
                with self.subTest(index=index):
                    if index == 0:
                        verify(candidate, archive)
                    else:
                        with self.assertRaises(ValueError):
                            verify(candidate, archive)
            (site / "calendar.ics").write_bytes(b"corrupted")
            with self.assertRaisesRegex(ValueError, "Candidate hash mismatch"):
                verify(candidate)
