"""Check real Actions artifact round trips without publishing or extracting tar files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def verify(candidate, pages_tar=None):
    site = (Path(candidate) / "site").resolve()
    report = json.loads((site / "status.json").read_text(encoding="utf-8"))
    revisions = json.loads((Path(candidate) / "events.json").read_text(encoding="utf-8"))
    if not isinstance(revisions.get("events"), dict):
        raise ValueError("Missing event revision history")
    expected = {"status.json": (site / "status.json").read_bytes()}
    for name, checksum in report["files"].items():
        path = (site / name).resolve()
        if site not in path.parents or path.is_symlink():
            raise ValueError("Unsafe candidate path: " + name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError("Candidate hash mismatch: " + name)
        expected[name] = raw
    if pages_tar is not None:
        # The Pages action intentionally excludes hidden markers such as .nojekyll.
        actual = {}
        with tarfile.open(pages_tar) as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("Unsafe archive path")
                if member.isdir():
                    continue
                name = str(path)
                if not member.isfile() or name in actual:
                    raise ValueError("Unexpected archive entry: " + name)
                actual[name] = archive.extractfile(member).read()
        if actual.keys() != expected.keys():
            raise ValueError("Pages archive file list differs from the candidate")
        if any(actual[name] != raw for name, raw in expected.items()):
            raise ValueError("Pages archive content differs from the candidate")
    print(f"Artifact verified: {report['release']}; {len(expected)} public files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--pages-tar", type=Path)
    args = parser.parse_args()
    verify(args.candidate, args.pages_tar)
