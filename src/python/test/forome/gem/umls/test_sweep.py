#!/usr/bin/env python3
"""Offline tests for the pre-registered mapping sweep (forome.gem.umls.sweep).

No network, no key: a StubClient returns canned candidates keyed by search
term, and every file the tests write goes to a pytest tmp_path. The real
protocol under data/umls/sweeps/ is only READ (to check it validates).
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from forome.gem.umls import sweep as S
from forome.gem.umls._paths import DATA_DIR

REAL_PROTOCOL = DATA_DIR / "sweeps" / "credibility.yaml"


def _cand(cui, name, sty="Qualitative Concept", src="MSH"):
    return {"cui": cui, "name": name, "root_source": src,
            "semantic_types": [sty]}


class StubClient:
    """search() returns canned candidates keyed by lower-cased term; every
    call is recorded so tests can assert what the protocol asked for."""

    kind = "stub"
    version = "TEST-2025"

    def __init__(self, by_term=None):
        self.by_term = {k.lower(): v for k, v in (by_term or {}).items()}
        self.calls: list[dict] = []

    def search(self, term, search_type="words", sabs=None, page_size=200,
               semantic_types=None, partial=False):
        self.calls.append({"term": term, "search_type": search_type,
                           "semantic_types": semantic_types, "partial": partial})
        return [dict(c) for c in self.by_term.get(term.lower(), [])]

    def atoms(self, cui, page_size=300):
        return [{"sab": "MSH", "language": "ENG"}, {"sab": "NCI", "language": "ENG"},
                {"sab": "MSHFRE", "language": "FRE"}]


class IndexedStubClient(StubClient):
    """A stub with a local index (concepts_by_tui), like a Postgres client."""

    def __init__(self, by_term=None, by_tui=None):
        super().__init__(by_term)
        self.by_tui = by_tui or {}

    def concepts_by_tui(self, tui):
        return [dict(c) for c in self.by_tui.get(tui, [])]


PROTOCOL = {
    "name": "t",
    "dimension": "credibility",
    "tokens": ["HIGH", "LOW"],
    "date_registered": "2026-08-30",
    "criteria": {"A": "denotation", "B": "granularity",
                 "C": "set membership", "D": "domain sense"},
    "axis_tuis": ["T080"],
    "passes": {
        "string": {"terms": ["high", "low"], "match": ["words", "normalizedWords"],
                   "scopes": ["all"]},
        "vocabulary": {"phrases": ["level of evidence"], "match": ["words", "partial"],
                       "scopes": ["all"]},
        "sty": {"tuis": ["T080"], "note": "needs local index"},
    },
}


def _write(tmp_path: Path, doc: dict, name="p.yaml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return p


# ---------------------------------------------------------------- protocol ---

def test_real_protocol_validates():
    p = S.load_protocol(REAL_PROTOCOL)
    assert p["name"] == "credibility"
    assert p["tokens"] == ["VERY_HIGH", "HIGH", "MEDIUM", "LOW"]
    assert set(p["criteria"]) >= {"A", "B", "C", "D"}
    assert list(p["passes"]) == ["string", "vocabulary", "sty"]
    assert "Level of Evidence" in p["notes"]


def test_protocol_loads(tmp_path):
    p = S.load_protocol(_write(tmp_path, PROTOCOL))
    assert p["dimension"] == "credibility"
    assert p["_path"].endswith("p.yaml")


@pytest.mark.parametrize("missing", S.REQUIRED_KEYS)
def test_protocol_missing_key_raises(tmp_path, missing):
    doc = {k: v for k, v in PROTOCOL.items() if k != missing}
    with pytest.raises(S.ProtocolError, match=missing):
        S.load_protocol(_write(tmp_path, doc))


def test_protocol_bad_values_raise(tmp_path):
    bad_match = dict(PROTOCOL, passes={"s": {"terms": ["x"], "match": ["fuzzy"]}})
    with pytest.raises(S.ProtocolError, match="fuzzy"):
        S.load_protocol(_write(tmp_path, bad_match))
    bad_scope = dict(PROTOCOL, passes={"s": {"terms": ["x"], "scopes": ["galaxy"]}})
    with pytest.raises(S.ProtocolError, match="galaxy"):
        S.load_protocol(_write(tmp_path, bad_scope))
    no_queries = dict(PROTOCOL, passes={"s": {"match": ["words"]}})
    with pytest.raises(S.ProtocolError, match="terms"):
        S.load_protocol(_write(tmp_path, no_queries))
    no_c = dict(PROTOCOL, criteria={"A": "a", "B": "b", "D": "d"})
    with pytest.raises(S.ProtocolError, match="A, B, C and D"):
        S.load_protocol(_write(tmp_path, no_c))
    empty_tokens = dict(PROTOCOL, tokens=[])
    with pytest.raises(S.ProtocolError, match="tokens"):
        S.load_protocol(_write(tmp_path, empty_tokens))


# ---------------------------------------------------------------- run() ------

def test_run_dedupes_and_merges_found_by():
    client = StubClient({
        "high": [_cand("C1", "High"), _cand("C2", "IPSS-R Risk Category High",
                                              "Finding", "NCI")],
        "low": [_cand("C3", "Low"), _cand("C1", "High")],  # C1 again
        "level of evidence": [_cand("C4", "Level of Evidence", "Intellectual Product",
                                    "NCI")],
    })
    r = S.run(PROTOCOL, client)

    cuis = [c["cui"] for c in r["candidates"]]
    assert cuis == ["C1", "C2", "C3", "C4"]        # deduped, discovery order
    c1 = r["candidates"][0]
    # 'high' x {words, normalizedWords} + 'low' x {words, normalizedWords}
    assert c1["found_by"] == [
        {"pass": "string", "q": "high", "match": "words"},
        {"pass": "string", "q": "high", "match": "normalizedWords"},
        {"pass": "string", "q": "low", "match": "words"},
        {"pass": "string", "q": "low", "match": "normalizedWords"},
    ]
    assert c1["fails"] is None and c1["why"] is None and c1["sabs"] == []

    # 2 terms x 2 match + 1 phrase x 2 match; sty skipped
    assert r["summary"] == {"n_queries": 6, "n_candidates": 4,
                            "by_pass": {"string": 3, "vocabulary": 1}}
    assert r["provider"] == {"kind": "stub", "umls": "TEST-2025"}
    assert r["protocol"]["tokens"] == ["HIGH", "LOW"]
    assert r["protocol"]["criteria"]["C"] == "set membership"

    by_name = {p["name"]: p for p in r["passes"]}
    assert by_name["string"]["status"] == "executed"
    assert [q["hits"] for q in by_name["string"]["queries"]] == [2, 2, 2, 2]
    # 'partial' is a words search with partialSearch=true, not a UTS searchType
    partial_calls = [c for c in client.calls if c["partial"]]
    assert len(partial_calls) == 1 and partial_calls[0]["search_type"] == "words"
    assert all(c["semantic_types"] is None for c in client.calls)  # scope: all


def test_run_scope_axis_passes_semantic_types():
    proto = dict(PROTOCOL, passes={"s": {"terms": ["high"], "match": ["exact"],
                                          "scopes": ["axis", "all"]}})
    client = StubClient({"high": [_cand("C1", "High")]})
    r = S.run(proto, client)
    axis_calls = [c for c in client.calls if c["semantic_types"]]
    assert len(axis_calls) == 1 and "T080" in axis_calls[0]["semantic_types"]
    assert r["passes"][0]["queries"][0]["scope"] == "axis"
    # without axis_tuis the axis query is recorded as skipped, not run
    proto2 = {k: v for k, v in proto.items() if k != "axis_tuis"}
    client2 = StubClient({"high": [_cand("C1", "High")]})
    r2 = S.run(proto2, client2)
    q = r2["passes"][0]["queries"][0]
    assert q["scope"] == "axis" and q["skipped"] and q["hits"] == 0
    assert r2["summary"]["n_queries"] == 1


def test_sty_pass_skipped_without_local_index():
    r = S.run(PROTOCOL, StubClient())
    sty = [p for p in r["passes"] if p["name"] == "sty"][0]
    assert sty["status"] == "skipped"
    assert sty["reason"] == "needs local index"
    assert sty["queries"] == []


def test_sty_pass_executed_with_local_index():
    client = IndexedStubClient(
        by_term={"high": [_cand("C1", "High")]},
        by_tui={"T080": [_cand("C1", "High"), _cand("C9", "Certainty")]})
    r = S.run(PROTOCOL, client)
    sty = [p for p in r["passes"] if p["name"] == "sty"][0]
    assert sty["status"] == "executed"
    assert sty["queries"] == [{"q": "T080", "match": "sty", "scope": "all", "hits": 2}]
    c1 = [c for c in r["candidates"] if c["cui"] == "C1"][0]
    assert {"pass": "sty", "q": "T080", "match": "sty"} in c1["found_by"]
    assert r["summary"]["by_pass"] == {"string": 1, "sty": 2}
    assert r["summary"]["n_candidates"] == 2


def test_limit_per_query_and_enrich():
    client = StubClient({"high": [_cand("C1", "High"), _cand("C2", "Higher"),
                                  _cand("C3", "Highest")]})
    proto = dict(PROTOCOL, passes={"s": {"terms": ["high"], "match": ["words"]}})
    r = S.run(proto, client, enrich=True, limit_per_query=2)
    assert [c["cui"] for c in r["candidates"]] == ["C1", "C2"]
    assert r["passes"][0]["queries"][0]["hits"] == 2
    assert r["candidates"][0]["sabs"] == ["MSH", "NCI"]   # English SABs only


def test_null_client_runs_clean():
    from forome.gem.umls.uts_client import NullClient
    r = S.run(PROTOCOL, NullClient())
    assert r["candidates"] == []
    assert r["provider"]["kind"] == "null"
    assert r["summary"]["n_queries"] == 6


# ---------------------------------------------------------------- merge ------

def test_prior_curation_survives_rerun(tmp_path):
    client = StubClient({"high": [_cand("C1", "High"), _cand("C2", "IPSS High")],
                         "low": [_cand("C3", "Low")]})
    first = S.run(PROTOCOL, client)
    # curator fills in two of three
    first["candidates"][1]["fails"] = "D"
    first["candidates"][1]["why"] = "MDS risk category, not an epistemic degree"
    first["candidates"][2]["fails"] = "C"
    first["candidates"][2]["why"] = "bare qualifier"
    out = tmp_path / "t.results.yaml"
    out.write_text(S.dump_results(first))

    # re-run: C3 no longer surfaced, C5 new
    client2 = StubClient({"high": [_cand("C1", "High"), _cand("C2", "IPSS High")],
                          "low": [_cand("C5", "Low level")]})
    second = S.merge_curation(S.run(PROTOCOL, client2), S.load_results(out))
    by = {c["cui"]: c for c in second["candidates"]}
    assert by["C2"]["fails"] == "D" and by["C2"]["why"].startswith("MDS")
    assert by["C1"]["fails"] is None and by["C5"]["fails"] is None
    assert second["stale_curation"] == [
        {"cui": "C3", "name": "Low", "fails": "C", "why": "bare qualifier"}]
    assert second["summary"]["n_carried_over"] == 1
    assert second["summary"]["n_curated"] == 1
    assert second["summary"]["n_stale_curation"] == 1

    # stale curation is itself carried forward if the CUI reappears later
    out.write_text(S.dump_results(second))
    third = S.merge_curation(S.run(PROTOCOL, client), S.load_results(out))
    by3 = {c["cui"]: c for c in third["candidates"]}
    assert by3["C3"]["fails"] == "C"
    assert "stale_curation" not in third


def test_merge_without_previous_is_identity():
    r = S.run(PROTOCOL, StubClient())
    assert S.merge_curation(r, None) is r
    assert S.load_results(Path("/nonexistent/x.yaml")) is None


# ---------------------------------------------------------------- tex --------

def test_render_tex_escapes_and_marks_unadjudicated():
    client = StubClient({
        "high": [_cand("C1", "High & Mighty 100%"),
                 _cand("C2", "IPSS_R High", "Finding", "NCI")],
    })
    r = S.run(PROTOCOL, client)
    r["candidates"][1]["fails"] = "D"
    r["candidates"][1]["why"] = "risk_category 50% & more"
    t = S.render_tex(r)
    assert r"High \& Mighty 100\%" in t
    assert r"IPSS\_R High" in t
    assert r"risk\_category 50\% \& more" in t
    assert "High & Mighty 100%" not in t
    assert r"\begin{longtable}" in t and r"\end{longtable}" in t
    assert r"\caption{" in t and "protocol" in t and "2026-08-30" in t
    assert "stub" in t and "TEST-2025" in t
    # preamble comment lists the criteria
    assert "%    A: denotation" in t and "%    D: domain sense" in t
    # unadjudicated row: '---' fails cell and an explicit marker
    row_c1 = [ln for ln in t.splitlines() if "(C1)" in ln][0]
    assert "& --- &" in row_c1 and r"\emph{not adjudicated}" in row_c1
    row_c2 = [ln for ln in t.splitlines() if "(C2)" in ln][0]
    assert "& D &" in row_c2 and "not adjudicated" not in row_c2
    # skipped pass is reported in the caption
    assert "skipped: sty" in t


def test_render_tex_sorted_by_pass_then_name():
    client = StubClient({
        "high": [_cand("C1", "zeta"), _cand("C2", "alpha")],
        "level of evidence": [_cand("C3", "Level of Evidence")],
    })
    t = S.render_tex(S.run(PROTOCOL, client))
    lines = t.splitlines()
    i_alpha = next(i for i, ln in enumerate(lines) if "(C2)" in ln)
    i_zeta = next(i for i, ln in enumerate(lines) if "(C1)" in ln)
    i_loe = next(i for i, ln in enumerate(lines) if "(C3)" in ln)
    assert i_alpha < i_zeta < i_loe
    assert lines[i_alpha - 1].endswith(r"{\textbf{pass: string}} \\")


# ---------------------------------------------------------------- CLI --------

def test_main_null_provider_writes_results_and_tex(tmp_path, monkeypatch):
    proto = _write(tmp_path, PROTOCOL)
    out = tmp_path / "res.yaml"
    texf = tmp_path / "sub" / "res.tex"
    rc = S.main([str(proto), "--provider", "null", "--out", str(out),
                 "--tex", str(texf), "--umls-release", "2025AA"])
    assert rc == 0
    doc = yaml.safe_load(out.read_text())
    assert doc["candidates"] == []
    assert doc["provider"] == {"kind": "null", "umls": "2025AA"}
    assert out.read_text().startswith("# GENERATED by gem-umls-sweep")
    assert r"\begin{longtable}" in texf.read_text()

    # default --out lands in SWEEPS_DIR/<name>.results.yaml (redirected here)
    monkeypatch.setattr(S, "SWEEPS_DIR", tmp_path / "sweeps")
    assert S.main([str(proto), "--provider", "null"]) == 0
    assert (tmp_path / "sweeps" / "t.results.yaml").is_file()


def test_main_invalid_protocol_returns_2(tmp_path, capsys):
    bad = _write(tmp_path, {k: v for k, v in PROTOCOL.items() if k != "passes"})
    assert S.main([str(bad), "--provider", "null"]) == 2
    assert "passes" in capsys.readouterr().err
