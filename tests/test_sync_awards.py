"""Tests for sync_awards.py — Phase 3a (ADR-024.1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_awards import (  # noqa: E402
    MdxAward,
    OrenuAward,
    compute_drift_warnings,
    match_pairs,
    run,
)


def make_orenu(title="PMP", org="PMI", scope="academic-honor", status="received") -> OrenuAward:
    return OrenuAward(
        award_id=f"oid-{hash(title) & 0xffff:04x}",
        person_display_name="Sarah Faria Alcantara Macedo Rodovalho",
        title=title,
        organization=org,
        organization_url=None,
        scope=scope,
        status=status,
        subcategory=None,
        period="2025",
        year_awarded=2025,
        description="x",
        external_url=None,
        hero_image_url=None,
    )


def make_mdx(title="PMP", org="PMI") -> MdxAward:
    return MdxAward(
        path=Path(title.lower().split()[0] + ".mdx"),
        frontmatter={"title": title, "organization": org},
        body="",
    )


def test_match_substring_either_direction():
    orenu = [make_orenu(title="CO+I Team Award")]
    mdx = [make_mdx(title="CO+I Team Award — Microsoft FY25 Q3")]
    matched, _, _ = match_pairs(orenu, mdx)
    assert len(matched) == 1


def test_match_full_title_into_short_mdx():
    orenu = [make_orenu(title="PMI LATAM Excellence Awards 2025 — Nominee")]
    mdx = [make_mdx(title="PMI LATAM")]
    matched, _, _ = match_pairs(orenu, mdx)
    assert len(matched) == 1


def test_stub_when_no_mdx():
    matched, u_o, _ = match_pairs([make_orenu(title="Brand New 2030")], [])
    assert not matched
    assert len(u_o) == 1


def test_orphan_when_no_orenu():
    matched, _, u_m = match_pairs([], [make_mdx(title="Old Award")])
    assert not matched
    assert len(u_m) == 1


def test_drift_title_warns_when_no_overlap():
    orenu = make_orenu(title="Completely Different Thing")
    mdx = make_mdx(title="PMP")
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("title:" in w for w in warnings)


def test_drift_org_warns_when_no_overlap():
    orenu = make_orenu(title="PMP", org="Apple Inc")
    mdx = make_mdx(title="PMP", org="Microsoft")
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("org:" in w for w in warnings)


def test_no_drift_when_substring_match_either_direction():
    orenu = make_orenu(title="PMP", org="PMI")
    mdx = make_mdx(title="PMP — Project Management Professional", org="Project Management Institute (PMI)")
    warnings = compute_drift_warnings(orenu, mdx)
    assert not warnings


def test_run_clean_state(tmp_path, capsys):
    cd = tmp_path / "awards"
    cd.mkdir()
    (cd / "pmp.mdx").write_text(
        "---\ntitle: PMP Award\norganization: PMI\nscope: academic-honor\ndescription: x\nperiod: '2025'\n---\n",
        encoding="utf-8",
    )
    orenu = [make_orenu(title="PMP Award", org="PMI")]
    exit_code = run(cd, apply=False, person_display_name="Sarah", orenu_override=orenu)
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "Matched pairs:     1" in out


def test_run_stub_exit_1(tmp_path, capsys):
    cd = tmp_path / "awards"
    cd.mkdir()
    orenu = [make_orenu(title="Some New 2030")]
    exit_code = run(cd, apply=False, person_display_name="Sarah", orenu_override=orenu)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "STUB NEEDED" in out


def test_run_orphan_exit_1(tmp_path, capsys):
    cd = tmp_path / "awards"
    cd.mkdir()
    (cd / "stale.mdx").write_text(
        "---\ntitle: Stale Old\norganization: X\nscope: academic-honor\ndescription: x\nperiod: '1999'\n---\n",
        encoding="utf-8",
    )
    exit_code = run(cd, apply=False, person_display_name="Sarah", orenu_override=[])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "ORPHAN MDX" in out
