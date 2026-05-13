"""Tests for sync_community.py — Phase 3b (ADR-024.1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_community import (  # noqa: E402
    MdxCommunity,
    OrenuCommunity,
    compute_drift_warnings,
    match_pairs,
    run,
)


def make_orenu(role="Mentor", org="PMI", current=False) -> OrenuCommunity:
    return OrenuCommunity(
        service_id=f"oid-{hash(role + org) & 0xffff:04x}",
        person_display_name="Vitor Maia Rodovalho",
        role=role,
        organization=org,
        organization_url=None,
        affiliation="2020 – 2021",
        start_year=2020,
        is_current=current,
        description="x",
        archive_links=[],
    )


def make_mdx(role="Mentor", org="PMI") -> MdxCommunity:
    return MdxCommunity(
        path=Path((role + org).lower().replace(" ", "-") + ".mdx"),
        frontmatter={"role": role, "organization": org},
        body="",
    )


def test_match_org_substring_either_direction():
    orenu = [make_orenu(org="PMI Brazil Goiás Chapter")]
    mdx = [make_mdx(org="PMI Brazil Goiás")]
    matched, _, _ = match_pairs(orenu, mdx)
    assert len(matched) == 1


def test_match_long_orenu_into_short_mdx():
    orenu = [make_orenu(org='Centro Acadêmico de Engenharia Civil (CAEC) · UEG')]
    mdx = [make_mdx(org='CAEC')]
    matched, _, _ = match_pairs(orenu, mdx)
    assert len(matched) == 1


def test_stub_when_no_mdx():
    matched, u_o, _ = match_pairs([make_orenu(org="Brand New Org")], [])
    assert not matched
    assert len(u_o) == 1


def test_orphan_when_no_orenu():
    matched, _, u_m = match_pairs([], [make_mdx(org="Old Org")])
    assert not matched
    assert len(u_m) == 1


def test_drift_role_warns_when_no_overlap():
    orenu = make_orenu(role="Very Different Role", org="PMI")
    mdx = make_mdx(role="Mentor", org="PMI")
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("role:" in w for w in warnings)


def test_drift_org_warns_when_no_overlap():
    orenu = make_orenu(role="Mentor", org="Different Org Inc")
    mdx = make_mdx(role="Mentor", org="PMI Brazil")
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("org:" in w for w in warnings)


def test_no_drift_when_substring_match():
    orenu = make_orenu(role="Mentor", org="PMI")
    mdx = make_mdx(role="Mentor at PMI", org="PMI Brazil Chapter")
    warnings = compute_drift_warnings(orenu, mdx)
    assert not warnings


def test_run_clean_state(tmp_path, capsys):
    cd = tmp_path / "community"
    cd.mkdir()
    (cd / "pmi.mdx").write_text(
        "---\nrole: Mentor\norganization: PMI Brazil Chapter\naffiliation: '2020 – 2021'\ndescription: x\n---\n",
        encoding="utf-8",
    )
    orenu = [make_orenu(role="Mentor", org="PMI Brazil")]
    exit_code = run(cd, apply=False, person_display_name="Vitor", orenu_override=orenu)
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "Matched pairs:     1" in out


def test_run_stub_exit_1(tmp_path, capsys):
    cd = tmp_path / "community"
    cd.mkdir()
    orenu = [make_orenu(org="New Org 2030")]
    exit_code = run(cd, apply=False, person_display_name="Vitor", orenu_override=orenu)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "STUB NEEDED" in out


def test_run_orphan_exit_1(tmp_path, capsys):
    cd = tmp_path / "community"
    cd.mkdir()
    (cd / "stale.mdx").write_text(
        "---\nrole: Old\norganization: Old Org\naffiliation: '1999'\ndescription: x\n---\n",
        encoding="utf-8",
    )
    exit_code = run(cd, apply=False, person_display_name="Vitor", orenu_override=[])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "ORPHAN MDX" in out
