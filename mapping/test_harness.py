#!/usr/bin/env python3
"""Offline unit tests for the UMLS crosswalk harness.

No network and no UMLS key: a StubClient exercises the status logic with full
control, and the FixtureClient (canned JSON under fixtures/) drives the whole
build + render pipeline. The synthetic CUIs (C9000001..) live only in the
fixtures and never enter the real crosswalk.

Run:  python3 mapping/test_harness.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_umls_crosswalk as H  # noqa: E402
import render_crosswalk_tex as R  # noqa: E402
import uts_client as U  # noqa: E402
from uts_client import FixtureClient, NullClient  # noqa: E402

FIXTURES = SCRIPT_DIR / "fixtures"


class StubClient:
    """Returns configured candidates keyed by search_type, for status tests."""

    def __init__(self, by_type=None):
        self.by_type = by_type or {}

    def search(self, term, search_type="words", sabs=None, page_size=200):
        return list(self.by_type.get(search_type, []))


def _cand(name, cui="C0000001"):
    return {"cui": cui, "name": name, "root_source": "MSH",
            "semantic_types": ["Test Type"]}


class TestResolveStatus(unittest.TestCase):
    def test_pending_when_not_live(self):
        r = H.resolve(StubClient(), "anything", None, live=False)
        self.assertEqual(r["status"], "pending")
        self.assertNotIn("cui", r)

    def test_mapped_via_exact(self):
        c = StubClient({"exact": [_cand("Genome-wide association study", "C9")]})
        r = H.resolve(c, "Genome-wide association study", None, live=True)
        self.assertEqual(r["status"], "mapped")
        self.assertEqual(r["search_type"], "exact")
        self.assertEqual(r["cui"], "C9")

    def test_exact_tier_with_mismatched_name_is_review(self):
        # Honesty regression: an 'exact'-tier hit whose name does NOT match the
        # query must be 'review', not silently 'mapped'.
        c = StubClient({"exact": [_cand("A completely different concept", "C9")]})
        r = H.resolve(c, "Genome-wide association study", None, live=True)
        self.assertEqual(r["status"], "review")
        self.assertEqual(r["cui"], "C9")  # candidate still recorded for the curator

    def test_accent_folding_allows_match(self):
        # _norm folds accents so an accented UMLS name still matches an ASCII query.
        c = StubClient({"exact": [_cand("Über Gene")]})
        r = H.resolve(c, "uber gene", None, live=True)
        self.assertEqual(r["status"], "mapped")

    def test_mapped_via_normalized_name_equal(self):
        # exact empty; normalized returns a name that normalises equal to query
        c = StubClient({"normalizedString": [_cand("In Vivo")]})
        r = H.resolve(c, "in vivo", None, live=True)
        self.assertEqual(r["status"], "mapped")
        self.assertEqual(r["search_type"], "normalizedString")

    def test_review_when_name_mismatch(self):
        c = StubClient({"words": [_cand("Something only loosely related")]})
        r = H.resolve(c, "Functional equivalence", None, live=True)
        self.assertEqual(r["status"], "review")
        self.assertEqual(len(r["candidates"]), 1)

    def test_unmapped_when_no_candidates(self):
        r = H.resolve(StubClient(), "no such concept", None, live=True)
        self.assertEqual(r["status"], "unmapped")


class TestClientParsing(unittest.TestCase):
    def test_semantic_types_string_and_dict_forms(self):
        # _normalise must handle semanticTypes as strings (search endpoint) and
        # as dicts (content endpoint), extracting names either way.
        s = U._normalise({"ui": "C1", "name": "X", "rootSource": "MSH",
                          "semanticTypes": ["Gene or Genome"]})
        self.assertEqual(s["semantic_types"], ["Gene or Genome"])
        d = U._normalise({"ui": "C2", "name": "Y", "rootSource": "MSH",
                          "semanticTypes": [{"name": "Finding",
                                             "uri": "http://x/T033"}]})
        self.assertEqual(d["semantic_types"], ["Finding"])


class TestInventory(unittest.TestCase):
    def test_loads_axis_and_values(self):
        entries = H.load_entries()
        self.assertGreater(len(entries), 40)
        kinds = {e["kind"] for e in entries}
        self.assertEqual(kinds, {"axis", "value", "common_value"})
        for e in entries:
            self.assertTrue(e["query"], f"empty query for {e}")

    def test_inventory_covers_shacl_enums(self):
        try:
            import rdflib  # noqa: F401
        except ImportError:
            self.skipTest("rdflib not installed")
        members = H.shacl_enum_members()
        self.assertIn("GWAS", members)
        self.assertIn("complete", members)
        tokens = {str(e["token"]) for e in H.load_entries() if e["token"]}
        missing = members - tokens
        self.assertFalse(missing, f"SHACL enum members not in inventory: {missing}")

    def test_check_inventory_returns_zero(self):
        try:
            import rdflib  # noqa: F401
        except ImportError:
            self.skipTest("rdflib not installed")
        self.assertEqual(H.check_inventory(), 0)


class TestBuildAndRender(unittest.TestCase):
    def test_build_with_null_client_is_all_pending(self):
        doc = H.build(NullClient(), live=False)
        self.assertEqual(doc["meta"]["counts"]["pending"], doc["meta"]["total"])
        self.assertEqual(doc["meta"]["counts"]["mapped"], 0)

    def test_build_with_fixtures_maps_known_terms(self):
        doc = H.build(FixtureClient(FIXTURES), live=True)
        by = {(e["dimension"], e["token"]): e for e in doc["entries"]}
        gwas = by[("method", "GWAS")]
        self.assertEqual(gwas["status"], "mapped")
        self.assertEqual(gwas["cui"], "C9000001")
        self.assertEqual(gwas["search_type"], "exact")
        # a term with no fixture is honestly unmapped, not invented
        self.assertEqual(by[("gene_relation", "X_inhibits_Y")]["status"], "unmapped")
        self.assertGreaterEqual(doc["meta"]["counts"]["mapped"], 3)

    def test_render_produces_valid_latex(self):
        doc = H.build(FixtureClient(FIXTURES), live=True)
        with tempfile.TemporaryDirectory() as d:
            cw = Path(d) / "cw.yaml"
            import yaml
            cw.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
            out = R.render(cw, R.DEFAULT_OMOP)
        self.assertIn(r"\section{UMLS and OMOP/CDM crosswalk}", out)
        self.assertEqual(out.count(r"\begin{longtable}"),
                         out.count(r"\end{longtable}"))
        self.assertEqual(out.count(r"\begin{longtable}"), 2)
        self.assertIn("C9000001", out)            # mapped CUI rendered
        self.assertIn("OMOP CDM", out)            # OMOP section present

    def test_render_escapes_special_chars(self):
        self.assertEqual(R.tex("a_b & c% {d}"), r"a\_b \& c\% \{d\}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
