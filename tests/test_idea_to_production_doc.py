"""The idea-to-production document is the pinned text."""

import hashlib
from pathlib import Path

EXPECTED_SHA256 = "4e1a14f774a0fe9bea36aa7ef75b1671c34f28fab88d089aed7b201b820868e4"
DOC = Path(__file__).resolve().parents[1] / "docs" / "process" / "idea-to-production.md"


def test_idea_to_production_sha256():
    digest = hashlib.sha256(DOC.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA256
