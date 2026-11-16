"""Every migration has its own revision id, and they form one chain with one head."""
import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parent.parent / 'migrations' / 'versions'


def _revisions():
    found = {}
    for path in VERSIONS.glob('*.py'):
        text = path.read_text()
        rev = re.search(r"^revision = '([^']+)'", text, re.M).group(1)
        down = re.search(r"^down_revision = (?:'([^']+)'|None)", text, re.M).group(1)
        found.setdefault(rev, []).append((path.name, down))
    return found


def test_revision_ids_are_unique():
    clashes = {rev: [name for name, _ in files] for rev, files in _revisions().items() if len(files) > 1}
    assert not clashes, f"Two migrations share a revision id: {clashes}"


def test_there_is_one_head():
    revisions = _revisions()
    pointed_at = {down for files in revisions.values() for _, down in files if down}
    heads = sorted(set(revisions) - pointed_at)
    assert len(heads) == 1, f"More than one head: {heads}"
