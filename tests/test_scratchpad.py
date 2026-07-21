"""Tests for scratchpad manager — notably the _splice_section function."""

from shared.scratchpad import _splice_section


class TestSpliceSection:
    def test_replace_existing_section(self):
        md = "## Plan\n\n1. Do thing\n\n## State\n\nactive\n"
        result = _splice_section(md, "Plan", "1. Do thing\n2. Done!")
        assert "## Plan" in result
        assert "2. Done!" in result
        assert "## State" in result
        assert "active" in result

    def test_create_new_section(self):
        md = "## Plan\n\n1. Do thing\n"
        result = _splice_section(md, "Notes", "Remember this")
        assert "## Notes" in result
        assert "Remember this" in result
        assert "## Plan" in result

    def test_empty_markdown(self):
        result = _splice_section("", "Section", "content")
        assert "## Section" in result
        assert "content" in result

    def test_preserves_other_sections(self):
        md = "## A\n\naaa\n\n## B\n\nbbb\n\n## C\n\nccc\n"
        result = _splice_section(md, "B", "replaced")
        assert "## A" in result
        assert "## C" in result
        assert "aaa" in result
        assert "ccc" in result
        assert "replaced" in result
        assert "bbb" not in result

    def test_multiline_headers(self):
        md = "## Intro\n\nSome intro text\n\n## Details\n\nLine1\nLine2\nLine3\n"
        result = _splice_section(md, "Details", "New line1\nNew line2")
        assert "New line1" in result
        assert "New line2" in result
        assert "Line1" not in result
