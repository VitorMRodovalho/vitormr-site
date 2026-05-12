"""
Tests for scripts/sync_publications.py — Phase 1a sync (ADR-024).

Coverage:
- title-matching helper handles the Orenu-short-title → MDX-full-title pattern
- dry-run against current production-mirroring fixture: exit 0, no updates
- citation update detected when Orenu has fresher data; written on --apply
- drift warning when Orenu title diverges from MDX beyond substring
- idempotency: second --apply run with no upstream changes produces no diff

These tests inject in-memory OrenuPublication objects (via the orenu_override
parameter on run()), so they do NOT need a live Postgres. The CI workflow
that actually hits Orenu runs separately (sync-publications.yml).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# Make the scripts/ directory importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_publications import (  # noqa: E402
    OrenuPublication,
    compute_citations_update,
    compute_drift_warnings,
    match_pairs,
    parse_frontmatter,
    run,
    title_matches,
)


# ─── Helpers ───────────────────────────────────────────────


def make_fixture_mdx(tmp_path: Path) -> Path:
    """Create a tmp content dir with one minimal MDX file."""
    content = tmp_path / "publications"
    content.mkdir()
    mdx = content / "ijac-2026-carbon-neutral-construction.mdx"
    mdx.write_text(
        "---\n"
        "title: \"Towards carbon-neutral construction: Integrating BIM and energy analysis for sustainable design decision-making\"\n"
        "kind: journal-article\n"
        "venue: International Journal of Architectural Computing\n"
        "year: 2026\n"
        "doi: \"10.1177/14780771241310213\"\n"
        "abstract: >\n"
        "  Test abstract.\n"
        "coAuthors:\n"
        "  - \"Gulbin Ozcan-Deniz\"\n"
        "  - \"Sarah Rodovalho\"\n"
        "citationsAt:\n"
        "  count: 3\n"
        "  observedOn: \"2026-05-09\"\n"
        "order: 1\n"
        "---\n"
        "\n"
        "Body content preserved.\n",
        encoding="utf-8",
    )
    return content


def make_orenu_carbon_neutral(citations: int = 3, observed: str = "2026-05-09") -> OrenuPublication:
    return OrenuPublication(
        publication_id="0e8d9c9e-8c38-4ae8-ba48-39ceb409b1ad",
        title="Towards Carbon-Neutral Construction",
        journal_name="International Journal of Architectural Computing",
        doi=None,
        published_at="2024-12-01",
        google_scholar_citations_count=citations,
        citations_last_audited_at=observed,
    )


# ─── Pure-function tests ───────────────────────────────────


def test_title_matches_substring():
    assert title_matches(
        "Towards Carbon-Neutral Construction",
        "Towards carbon-neutral construction: Integrating BIM and energy analysis",
    )


def test_title_matches_case_insensitive_punctuation_insensitive():
    assert title_matches("Foo: Bar", "foo bar baz")


def test_title_no_match():
    assert not title_matches("Quantum Foam", "Towards Carbon-Neutral Construction")


def test_title_matches_unicode_subscript():
    """Orenu 'CO2' must match MDX 'CO₂' (Unicode subscript)."""
    assert title_matches(
        "Analyzing CO2 Emissions by CSI Categories",
        "Analyzing CO₂ Emissions by CSI Categories: A Life Cycle Perspective",
    )


def test_title_matches_unicode_superscript():
    """And the same for superscript digits if anyone uses them."""
    assert title_matches("CO2 greenhouse gas", "CO² greenhouse gas effects in atmospheric studies")


def test_citations_mdx_fresher_skips_overwrite():
    """If MDX observed-on is more recent than Orenu's, do not overwrite."""
    from sync_publications import MdxPublication

    orenu = make_orenu_carbon_neutral(citations=3, observed="2026-04-29")
    mdx = MdxPublication(
        path=Path("x"),
        frontmatter={"citationsAt": {"count": 3, "observedOn": "2026-05-09"}},
        body="",
    )
    # MDX is fresher (May > April); should NOT overwrite.
    assert compute_citations_update(orenu, mdx) is None


def test_citations_orenu_fresher_overwrites():
    from sync_publications import MdxPublication

    orenu = make_orenu_carbon_neutral(citations=5, observed="2026-12-01")
    mdx = MdxPublication(
        path=Path("x"),
        frontmatter={"citationsAt": {"count": 3, "observedOn": "2026-05-09"}},
        body="",
    )
    result = compute_citations_update(orenu, mdx)
    assert result == {"count": 5, "observedOn": "2026-12-01"}


def test_citations_bootstrap_when_mdx_has_none():
    from sync_publications import MdxPublication

    orenu = make_orenu_carbon_neutral(citations=3, observed="2026-05-09")
    mdx = MdxPublication(path=Path("x"), frontmatter={}, body="")
    result = compute_citations_update(orenu, mdx)
    assert result == {"count": 3, "observedOn": "2026-05-09"}


def test_citations_update_returns_new_when_count_differs():
    orenu = make_orenu_carbon_neutral(citations=5, observed="2026-06-01")
    mdx_fm = {"citationsAt": {"count": 3, "observedOn": "2026-05-09"}}
    from sync_publications import MdxPublication

    mdx = MdxPublication(path=Path("x"), frontmatter=mdx_fm, body="")
    assert compute_citations_update(orenu, mdx) == {"count": 5, "observedOn": "2026-06-01"}


def test_citations_update_returns_none_when_unchanged():
    orenu = make_orenu_carbon_neutral(citations=3, observed="2026-05-09")
    from sync_publications import MdxPublication

    mdx = MdxPublication(
        path=Path("x"),
        frontmatter={"citationsAt": {"count": 3, "observedOn": "2026-05-09"}},
        body="",
    )
    assert compute_citations_update(orenu, mdx) is None


def test_drift_warning_when_orenu_title_outside_mdx():
    from sync_publications import MdxPublication

    orenu = OrenuPublication(
        publication_id="x",
        title="Quantum Foam Predictions",
        journal_name=None,
        doi=None,
        published_at=None,
        google_scholar_citations_count=0,
        citations_last_audited_at=None,
    )
    mdx = MdxPublication(
        path=Path("x"),
        frontmatter={"title": "Towards Carbon-Neutral Construction"},
        body="",
    )
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("title:" in w for w in warnings)


def test_drift_year_not_checked_phase_1a():
    """Phase 1a does NOT compute year drift — published_at vs print-issue-year
    are different semantic fields Orenu can't yet distinguish.
    """
    from sync_publications import MdxPublication

    orenu = OrenuPublication(
        publication_id="x",
        title="Test",
        journal_name=None,
        doi=None,
        published_at="2020-12-01",
        google_scholar_citations_count=0,
        citations_last_audited_at=None,
    )
    mdx = MdxPublication(
        path=Path("x"),
        frontmatter={"title": "Test", "year": 2026},
        body="",
    )
    warnings = compute_drift_warnings(orenu, mdx)
    assert not any("year:" in w for w in warnings)


def test_drift_doi_mismatch_warns():
    from sync_publications import MdxPublication

    orenu = OrenuPublication(
        publication_id="x",
        title="Test",
        journal_name=None,
        doi="10.1234/foo",
        published_at=None,
        google_scholar_citations_count=0,
        citations_last_audited_at=None,
    )
    mdx = MdxPublication(
        path=Path("x"),
        frontmatter={"title": "Test", "doi": "10.5555/bar"},
        body="",
    )
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("doi:" in w for w in warnings)


def test_match_pairs_doi_first_then_title():
    from sync_publications import MdxPublication

    orenu_with_doi = OrenuPublication(
        publication_id="a",
        title="Different",
        journal_name=None,
        doi="10.1234/foo",
        published_at=None,
        google_scholar_citations_count=0,
        citations_last_audited_at=None,
    )
    mdx_doi = MdxPublication(
        path=Path("a.mdx"),
        frontmatter={"title": "Whatever", "doi": "10.1234/foo"},
        body="",
    )
    mdx_title = MdxPublication(
        path=Path("b.mdx"),
        frontmatter={"title": "Different content here"},
        body="",
    )
    matched, _, _ = match_pairs([orenu_with_doi], [mdx_doi, mdx_title])
    # Should match on DOI even though title would also match.
    assert len(matched) == 1
    assert matched[0][1].path == Path("a.mdx")


# ─── End-to-end run() tests ────────────────────────────────


def test_run_dry_run_matched_unchanged_state(tmp_path, capsys):
    content_dir = make_fixture_mdx(tmp_path)
    orenu_pubs = [make_orenu_carbon_neutral()]
    exit_code = run(content_dir, apply=False, orenu_override=orenu_pubs)
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "Matched pairs:     1" in out
    assert "Citation updates planned: 0" in out
    assert "Drift warnings" in out


def test_run_applies_citation_update(tmp_path, capsys):
    content_dir = make_fixture_mdx(tmp_path)
    orenu_pubs = [make_orenu_carbon_neutral(citations=42, observed="2026-12-31")]
    exit_code = run(content_dir, apply=True, orenu_override=orenu_pubs)
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "UPDATE citations" in out
    # Verify the file was actually written.
    mdx_text = (content_dir / "ijac-2026-carbon-neutral-construction.mdx").read_text()
    fm, body = parse_frontmatter(mdx_text)
    assert fm["citationsAt"] == {"count": 42, "observedOn": "2026-12-31"}
    assert "Body content preserved." in body


def test_run_idempotent_after_apply(tmp_path, capsys):
    content_dir = make_fixture_mdx(tmp_path)
    orenu_pubs = [make_orenu_carbon_neutral(citations=42, observed="2026-12-31")]
    # First run: applies update.
    run(content_dir, apply=True, orenu_override=orenu_pubs)
    capsys.readouterr()  # discard
    # Second run: should be no-op.
    exit_code = run(content_dir, apply=True, orenu_override=orenu_pubs)
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "Citation updates planned: 0" in out


def test_run_unmatched_orenu_row_warns(tmp_path, capsys):
    content_dir = make_fixture_mdx(tmp_path)
    extra_orenu = OrenuPublication(
        publication_id="zzz",
        title="A New Paper Not Yet on Site",
        journal_name="Journal of Imaginary Studies",
        doi=None,
        published_at="2026-01-01",
        google_scholar_citations_count=0,
        citations_last_audited_at=None,
    )
    orenu_pubs = [make_orenu_carbon_neutral(), extra_orenu]
    exit_code = run(content_dir, apply=False, orenu_override=orenu_pubs)
    out = capsys.readouterr().out
    assert exit_code == 1, out
    assert "STUB NEEDED" in out


def test_run_orphan_mdx_warns(tmp_path, capsys):
    content_dir = make_fixture_mdx(tmp_path)
    # No Orenu rows → the existing MDX becomes an orphan.
    exit_code = run(content_dir, apply=False, orenu_override=[])
    out = capsys.readouterr().out
    assert exit_code == 1, out
    assert "ORPHAN MDX" in out
