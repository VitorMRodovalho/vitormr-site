"""
Tests for scripts/sync_credentials.py — Phase 2 sync (ADR-024).

Coverage:
- match_pairs() handles Sarah's 6 credentials matched to MDX
- compute_field_updates() detects status/date changes, ignores unchanged
- compute_drift_warnings() catches title + issuer mismatches
- enum normalization: Orenu 'in_progress' → MDX 'in-progress';
  Orenu 'lapsed' → MDX 'expired'
- end-to-end run() in dry-run + apply with idempotency
- stub-needed + orphan-MDX exit code 1
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sync_credentials import (  # noqa: E402
    MdxCredential,
    OrenuCredential,
    apply_updates_to_mdx,
    compute_drift_warnings,
    compute_field_updates,
    match_pairs,
    run,
)
from sync_publications import parse_frontmatter  # noqa: E402


def make_orenu(
    name: str = "PMP",
    kind: str = "certification",
    issuer: str = "PMI",
    status: str = "active",
    issued: str | None = None,
    expires: str | None = None,
    verify_url: str | None = None,
) -> OrenuCredential:
    return OrenuCredential(
        credential_id=f"oid-{hash(name) & 0xffff:04x}",
        person_display_name="Sarah Faria Alcantara Macedo Rodovalho",
        name=name,
        kind=kind,
        issuer=issuer,
        issuer_url=None,
        status=status,
        issued_date=issued,
        expires_date=expires,
        verify_url=verify_url,
        credly_badge_url=None,
    )


def make_mdx(
    title: str = "PMP",
    organization: str = "PMI",
    status: str = "active",
    **extra,
) -> MdxCredential:
    fm = {"title": title, "organization": organization, "status": status, **extra}
    return MdxCredential(
        path=Path(title.lower().split()[0] + ".mdx"),
        frontmatter=fm,
        body="",
    )


# ─── match_pairs ───


def test_match_sarah_6_credentials():
    """All 6 of Sarah's credentials match cleanly."""
    orenu = [
        make_orenu("Project Management Professional (PMP)"),
        make_orenu("LEED Green Associate (LEED GA)", kind="designation", issuer="USGBC/GBCI"),
        make_orenu("OSHA 30-Hour Construction Safety", issuer="OSHA"),
        make_orenu("AIA Associate (Assoc. AIA)", kind="membership", issuer="AIA"),
        make_orenu("Brazilian Architecture & Urbanism License", kind="license", issuer="CAU/BR"),
        make_orenu("NCARB Licensure", kind="license", status="in_progress"),
    ]
    mdx = [
        make_mdx(title="Project Management Professional (PMP)"),
        make_mdx(title="LEED Green Associate (LEED GA)"),
        make_mdx(title="OSHA 30-Hour Construction Safety"),
        make_mdx(title="AIA Associate (Assoc. AIA)"),
        make_mdx(title="Brazilian Architecture & Urbanism License"),
        make_mdx(title="NCARB Licensure", status="in-progress"),
    ]
    matched, u_o, u_m = match_pairs(orenu, mdx)
    assert len(matched) == 6
    assert not u_o
    assert not u_m


def test_match_short_orenu_into_long_mdx():
    """Orenu title is shorter than MDX title (common pattern)."""
    orenu = [make_orenu("LEED GA")]
    mdx = [make_mdx(title="LEED Green Associate (LEED GA)")]
    matched, _, _ = match_pairs(orenu, mdx)
    assert len(matched) == 1


# ─── compute_field_updates ───


def test_status_update_orenu_authoritative():
    orenu = make_orenu(status="expired")
    mdx = make_mdx(status="active")
    updates = compute_field_updates(orenu, mdx)
    assert updates == {"status": "expired"}


def test_enum_normalization_in_progress():
    """Orenu 'in_progress' (underscore) → MDX 'in-progress' (hyphen)."""
    orenu = make_orenu(status="in_progress")
    mdx = make_mdx(status="active")
    updates = compute_field_updates(orenu, mdx)
    assert updates == {"status": "in-progress"}


def test_lapsed_maps_to_expired():
    """Orenu 'lapsed' (deliberately discontinued) → MDX 'expired' (UI surface)."""
    orenu = make_orenu(status="lapsed")
    mdx = make_mdx(status="active")
    updates = compute_field_updates(orenu, mdx)
    assert updates == {"status": "expired"}


def test_issued_date_update():
    orenu = make_orenu(issued="2025-02-24")
    mdx = make_mdx()  # no issuedDate
    updates = compute_field_updates(orenu, mdx)
    assert updates.get("issuedDate") == "2025-02-24"


def test_validthrough_update():
    orenu = make_orenu(expires="2027-02-23")
    mdx = make_mdx()
    updates = compute_field_updates(orenu, mdx)
    assert updates.get("validThrough") == "2027-02-23"


def test_no_updates_when_unchanged():
    orenu = make_orenu(status="active", issued="2025-01-01", expires="2027-01-01")
    mdx = make_mdx(status="active", issuedDate="2025-01-01", validThrough="2027-01-01")
    updates = compute_field_updates(orenu, mdx)
    assert not updates


# ─── compute_drift_warnings ───


def test_drift_title_mismatch():
    orenu = make_orenu(name="Completely Different Credential")
    mdx = make_mdx(title="PMP")
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("title:" in w for w in warnings)


def test_drift_issuer_mismatch():
    orenu = make_orenu(name="PMP", issuer="Some Other Org")
    mdx = make_mdx(title="PMP", organization="PMI Project Management")
    warnings = compute_drift_warnings(orenu, mdx)
    assert any("org:" in w for w in warnings)


def test_no_drift_when_substring_match():
    orenu = make_orenu(name="PMP", issuer="PMI")
    mdx = make_mdx(title="PMP Project Management Professional", organization="Project Management Institute (PMI)")
    warnings = compute_drift_warnings(orenu, mdx)
    # Title substring match + issuer substring match → no warnings.
    assert not warnings


# ─── End-to-end run() ───


def test_run_idempotent_clean(tmp_path, capsys):
    cd = tmp_path / "credentials"
    cd.mkdir()
    (cd / "pmp.mdx").write_text(
        "---\n"
        "title: Project Management Professional (PMP)\n"
        "organization: PMI\n"
        "status: active\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )
    orenu = [make_orenu(name="Project Management Professional (PMP)", issuer="PMI")]
    exit_code = run(cd, apply=False, person_display_name="Sarah", orenu_override=orenu)
    out = capsys.readouterr().out
    assert exit_code == 0, out
    assert "Field updates planned: 0" in out


def test_run_applies_status_update(tmp_path, capsys):
    cd = tmp_path / "credentials"
    cd.mkdir()
    (cd / "pmp.mdx").write_text(
        "---\n"
        "title: PMP\n"
        "organization: PMI\n"
        "status: active\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )
    orenu = [make_orenu(name="PMP", issuer="PMI", status="expired")]
    exit_code = run(cd, apply=True, person_display_name="Sarah", orenu_override=orenu)
    assert exit_code == 0
    fm, _ = parse_frontmatter((cd / "pmp.mdx").read_text())
    assert fm["status"] == "expired"


def test_run_stub_when_no_mdx(tmp_path, capsys):
    cd = tmp_path / "credentials"
    cd.mkdir()
    orenu = [make_orenu(name="Brand New Credential 2030")]
    exit_code = run(cd, apply=False, person_display_name="Sarah", orenu_override=orenu)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "STUB NEEDED" in out


def test_run_orphan_when_no_orenu(tmp_path, capsys):
    cd = tmp_path / "credentials"
    cd.mkdir()
    (cd / "stale.mdx").write_text(
        "---\ntitle: Stale Old Credential\norganization: X\nstatus: active\n---\n",
        encoding="utf-8",
    )
    exit_code = run(cd, apply=False, person_display_name="Sarah", orenu_override=[])
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "ORPHAN MDX" in out
