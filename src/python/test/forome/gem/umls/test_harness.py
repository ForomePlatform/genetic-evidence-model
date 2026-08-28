#!/usr/bin/env python3
"""Offline unit tests for the UMLS crosswalk harness.

No network and no UMLS key: a StubClient exercises the status logic with full
control, and the FixtureClient (canned JSON under fixtures/) drives the whole
build + render pipeline. The synthetic CUIs (C9000001..) live only in the
fixtures and never enter the real crosswalk.

Run:  python3 mapping/test_harness.py
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forome.gem.umls import build_umls_crosswalk as H
from forome.gem.umls import render_crosswalk_tex as R
from forome.gem.umls import uts_client as U
from forome.gem.umls.uts_client import FixtureClient, NullClient
from forome.gem.umls._paths import DATA_DIR

FIXTURES = DATA_DIR / "fixtures"


class StubClient:
    """Returns configured candidates keyed by search_type, for status tests."""

    def __init__(self, by_type=None):
        self.by_type = by_type or {}

    def search(self, term, search_type="words", sabs=None, page_size=200,
               semantic_types=None):
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


class TestAdjudication(unittest.TestCase):
    def _entry(self):
        return {"dimension": "method", "token": "GWAS", "status": "review",
                "candidates": [{"cui": "C1", "name": "Genome-Wide Association Study",
                                "root_source": "MSH", "semantic_types": ["Research Activity"]}]}

    def test_accept_valid_cui_maps_and_marks_curated(self):
        r = H.apply_adjudication(self._entry(), {"accept": "C1", "note": "ok"})
        self.assertEqual(r["status"], "mapped")
        self.assertTrue(r["curated"])
        self.assertEqual(r["cui"], "C1")
        self.assertEqual(r["matched_name"], "Genome-Wide Association Study")

    def test_accept_cui_not_in_candidates_refuses_to_fabricate(self):
        r = H.apply_adjudication(self._entry(), {"accept": "C9999"})
        self.assertEqual(r["status"], "review")  # NOT mapped
        self.assertFalse(r["curated"])
        self.assertIn("curator_error", r)

    def test_unmapped_decision(self):
        r = H.apply_adjudication(self._entry(), {"unmapped": True, "note": "no concept"})
        self.assertEqual(r["status"], "unmapped")
        self.assertTrue(r["curated"])

    def test_build_applies_adjudications(self):
        adj = {"method/GWAS": {"accept": "C9000001"}}
        doc = H.build(FixtureClient(FIXTURES), live=True, adjudications=adj)
        by = {(e["dimension"], e["token"]): e for e in doc["entries"]}
        self.assertTrue(by[("method", "GWAS")].get("curated"))
        self.assertGreaterEqual(doc["meta"]["counts"]["curated"], 1)

    def test_accept_fetches_concept_when_not_in_candidates(self):
        class FetchClient:
            def get_concept(self, cui):
                return {"cui": cui, "name": "Fetched Concept",
                        "root_source": "MTH", "semantic_types": ["X"]}
        r = H.apply_adjudication(self._entry(), {"accept": "C7777"}, client=FetchClient())
        self.assertEqual(r["status"], "mapped")
        self.assertTrue(r["fetched"])
        self.assertEqual(r["matched_name"], "Fetched Concept")

    def test_accept_unconfirmable_cui_stays_review(self):
        class NoneClient:
            def get_concept(self, cui):
                return None
        r = H.apply_adjudication(self._entry(), {"accept": "C7777"}, client=NoneClient())
        self.assertEqual(r["status"], "review")
        self.assertFalse(r["curated"])


class TestAdjudicateUI(unittest.TestCase):
    def test_order_defs_prefers_english_and_pref_source(self):
        from forome.gem.umls import adjudicate_ui as A
        out = A.order_defs([{"source": "MSHCZE", "value": "cz"},
                            {"source": "NCI", "value": "n"},
                            {"source": "MSH", "value": "m"}])
        self.assertEqual(out[0]["source"], "MSH")           # MSH ranked above NCI
        self.assertTrue(all(not d["source"].endswith("CZE") for d in out))

    def test_load_state_merges_status_and_meaning(self):
        from forome.gem.umls import adjudicate_ui as A
        st = A.load_state()
        self.assertEqual(len(st["entries"]), 88)
        gwas = next(e for e in st["entries"] if e["token"] == "GWAS")
        self.assertEqual(gwas["dim_sty_name"], "Research Activity")
        self.assertEqual(gwas["dim_sty_tree"], "B1.3.2")
        self.assertEqual(gwas["sab_pref"], "MSH")
        self.assertEqual(gwas["status"], "mapped")
        self.assertTrue(gwas["meaning"])

    def test_concept_evidence_assembles(self):
        from forome.gem.umls import adjudicate_ui as A

        class EvClient:
            def get_concept(self, cui):
                return {"cui": cui, "name": "X", "status": "R", "atom_count": 3,
                        "semantic_type_details": [{"name": "Nucleotide Sequence", "tui": "T086"}]}

            def atoms(self, cui, page_size=300):
                return [{"sab": "NCI", "tty": "PT", "name": "X", "code": "c",
                         "obsolete": False, "suppressible": False},
                        {"sab": "MSH", "tty": "MH", "name": "x", "code": "d",
                         "obsolete": True, "suppressible": False}]

            def relations(self, cui, page_size=400):
                return [
                    # true is_a parent / child. UMLS orientation: rela=="isa"
                    # means the related concept is the PARENT (up); inverse_isa
                    # is the child (down). rel (PAR/CHD) is deliberately the
                    # "wrong" way round to prove we key on rela, not rel.
                    {"rel": "CHD", "rela": "isa", "related_cui": "C2", "related_name": "Parent", "sab": "NCI"},
                    {"rel": "PAR", "rela": "inverse_isa", "related_cui": "C3", "related_name": "Child", "sab": "MSH"},
                    # MeSH thematic-tree edge (empty rela) -- must NOT be is_a
                    {"rel": "PAR", "rela": "", "related_cui": "C9", "related_name": "Thematic", "sab": "MSH"},
                    # a meaningful labelled relation -> other_relations
                    {"rel": "RO", "rela": "gene_mapped_to_disease", "related_cui": "C4", "related_name": "Some Disease", "sab": "NCI"},
                    # lexical bookkeeping -- must be dropped from other_relations
                    {"rel": "SY", "rela": "has_alias", "related_cui": "C5", "related_name": "Alias", "sab": "NCI"},
                    # non-English source -- must be filtered everywhere
                    {"rel": "CHD", "rela": "isa", "related_cui": "C6", "related_name": "Padre", "sab": "SCTSPA"}]

            def rollup(self, cui, **k):
                return [{"name": "Parent", "code": "C2", "sab": "NCI"}]

        saved = A.client
        try:
            A.client = EvClient()
            ev = A.concept_evidence("C1", "T082")
        finally:
            A.client = saved
        self.assertEqual(ev["sty_path"][-1]["tui"], "T082")   # climbs to axis type
        self.assertTrue(ev["under_axis"])
        self.assertEqual(set(ev["sabs"]), {"NCI", "MSH"})
        self.assertEqual({a["sab"] for a in ev["atom_rows"]}, {"NCI", "MSH"})
        self.assertTrue(any(r["dir"] == "up" and r["name"] == "Parent" for r in ev["relations"]))
        self.assertTrue(any(r["dir"] == "down" and r["name"] == "Child" for r in ev["relations"]))
        names = {r["name"] for r in ev["relations"]}
        self.assertNotIn("Thematic", names)   # empty-rela tree edge is not is_a
        self.assertNotIn("Padre", names)      # SCTSPA is non-English -> filtered
        by_rela = {g["rela"]: g for g in ev["other_relations"]}
        self.assertIn("gene_mapped_to_disease", by_rela)
        self.assertEqual(by_rela["gene_mapped_to_disease"]["items"][0]["name"], "Some Disease")
        self.assertNotIn("has_alias", by_rela)   # lexical bookkeeping dropped


class TestSemanticTypes(unittest.TestCase):
    def test_subtree_includes_descendants_excludes_others(self):
        from forome.gem.umls import semantic_types as S
        sub = S.subtree_tuis("T082")           # Spatial Concept (A2.1.5)
        self.assertIn("T082", sub)
        self.assertIn("T086", sub)             # Nucleotide Sequence (A2.1.5.3.1)
        self.assertNotIn("T028", sub)          # Gene or Genome (not under A2.1.5)

    def test_filter_param_comma_joined(self):
        from forome.gem.umls import semantic_types as S
        f = S.filter_param("T082")
        self.assertIn("T082", f)
        self.assertIn(",", f)
        self.assertIsNone(S.filter_param(None))

    def test_build_types_axes_and_resolution_is_spatial(self):
        doc = H.build(FixtureClient(FIXTURES), live=True)
        axes = [e for e in doc["entries"] if e["kind"] == "axis"]
        typed = [e for e in axes if e.get("sty_tui")]
        self.assertGreaterEqual(len(typed), 8)
        res = next(e for e in axes if e["dimension"] == "resolution")
        self.assertEqual(res["sty_tui"], "T082")
        self.assertEqual(res["status"], "mapped")

    def test_path_to_climbs_to_axis(self):
        from forome.gem.umls import semantic_types as S
        p = S.path_to("T086", "T082")   # Nucleotide Sequence -> ... -> Spatial Concept
        self.assertEqual(p[0]["tui"], "T086")
        self.assertEqual(p[-1]["tui"], "T082")
        self.assertIn("T085", [x["tui"] for x in p])

    def test_most_specific_is_deepest(self):
        from forome.gem.umls import semantic_types as S
        self.assertEqual(S.most_specific(["T082", "T086"]), "T086")


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

    def test_build_only_dims_is_scoped(self):
        """A scoped rebuild resolves just the requested dimension; its entries
        match the full build's entries for that dimension."""
        part = H.build(FixtureClient(FIXTURES), live=True, only_dims={"method"})
        self.assertTrue(part["entries"])
        self.assertEqual({e["dimension"] for e in part["entries"]}, {"method"})
        full = H.build(FixtureClient(FIXTURES), live=True)
        want = [e for e in full["entries"] if e["dimension"] == "method"]
        self.assertEqual(part["entries"], want)
        counts = part["meta"]["counts"]
        self.assertEqual(sum(counts[s] for s in
                             ("mapped", "review", "unmapped", "pending")),
                         len(part["entries"]))

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


class TestAxisBuilder(unittest.TestCase):
    """The standalone axis builder: works against an empty workspace, writes the
    inventory, and surfaces axes even before any crosswalk exists."""

    def test_empty_workspace_build_and_modify_axis(self):
        from forome.gem.umls import adjudicate_ui as A
        ws = Path(tempfile.mkdtemp()) / "mapping"   # empty, does not exist yet
        saved = (A.CROSSWALK, H.INVENTORY, H.ADJUDICATIONS)
        try:
            A.CROSSWALK = ws / "umls_crosswalk.yaml"
            H.INVENTORY = ws / "dimensions_inventory.yaml"
            H.ADJUDICATIONS = ws / "adjudications.yaml"

            # empty workspace -> no dimensions, but the app still loads
            st = A.load_state()
            self.assertEqual(st["entries"], [])
            self.assertEqual(st["dimensions"], [])

            # construct a new axis from scratch -> inventory is created
            ax = A.save_axis("resolution", semantic_type="T082",
                             query="Spatial concept", note="from scratch")
            self.assertEqual(ax["semantic_type"], "T082")
            self.assertTrue(H.INVENTORY.is_file())

            # it now shows up as a typed axis with the value-search filter
            e = next(x for x in A.load_state()["entries"] if x["dimension"] == "resolution")
            self.assertEqual(e["kind"], "axis")
            self.assertEqual((e["sty_tui"], e["sty_tree"]), ("T082", "A2.1.5"))
            self.assertTrue(e["in_inventory"])
            self.assertIn("T082", e["dim_sty_filter"])

            # modify: retype, and query/note are preserved
            A.save_axis("resolution", semantic_type="T086")
            e = next(x for x in A.load_state()["entries"] if x["dimension"] == "resolution")
            self.assertEqual(e["sty_tui"], "T086")
            self.assertEqual(e["axis_query"], "Spatial concept")

            # an unknown semantic type is refused (honest by construction)
            with self.assertRaises(ValueError):
                A.save_axis("bad", semantic_type="T999")
        finally:
            A.CROSSWALK, H.INVENTORY, H.ADJUDICATIONS = saved

    def test_tiered_ordering_and_metadata(self):
        """Dimensions order core -> conditional -> candidate by their `order`
        keys (never the alphabet), axis entries carry tier/activation, and
        save_axis persists tier metadata for the navigation."""
        from forome.gem.umls import adjudicate_ui as A
        ws = Path(tempfile.mkdtemp()) / "mapping"
        saved = (A.CROSSWALK, H.INVENTORY, H.ADJUDICATIONS)
        try:
            A.CROSSWALK = ws / "umls_crosswalk.yaml"
            H.INVENTORY = ws / "dimensions_inventory.yaml"
            H.ADJUDICATIONS = ws / "adjudications.yaml"

            # alphabetical would give: aaa_conditional, credibility, method
            A.save_axis("method", semantic_type="T062", query="Methods",
                        tier="core", order=20)
            A.save_axis("credibility", query="Certainty of evidence",
                        tier="core", order=50)
            A.save_axis("aaa_conditional", query="x", tier="conditional",
                        order=110, activation="knowledge_domain: GENE_FUNCTION")
            st = A.load_state()
            self.assertEqual([e["dimension"] for e in st["entries"]],
                             ["method", "credibility", "aaa_conditional"])

            by = {e["dimension"]: e for e in st["entries"]}
            self.assertEqual(by["method"]["tier"], "core")
            self.assertTrue(by["method"]["tier_explicit"])
            self.assertIsNone(by["method"]["activation"])
            self.assertEqual(by["aaa_conditional"]["tier"], "conditional")
            self.assertEqual(by["aaa_conditional"]["activation"],
                             "knowledge_domain: GENE_FUNCTION")

            # a dimension saved without tier defaults to core, flagged implicit
            A.save_axis("untiered", query="y")
            e = next(x for x in A.load_state()["entries"]
                     if x["dimension"] == "untiered")
            self.assertEqual(e["tier"], "core")
            self.assertFalse(e["tier_explicit"])

            # an unknown tier is refused
            with self.assertRaises(ValueError):
                A.save_axis("bad", tier="fundamental")
            # names that would break YAML keys / UI handlers are refused,
            # and a non-integer order is a validation error, not a crash
            with self.assertRaises(ValueError):
                A.save_axis("curator's_pick")
            with self.assertRaises(ValueError):
                A.save_axis("method", order="abc")
        finally:
            A.CROSSWALK, H.INVENTORY, H.ADJUDICATIONS = saved

    def test_repo_inventory_is_fully_tiered(self):
        """The repo's own inventory carries explicit tier metadata on every
        dimension, core ones ordered per the schema's canonical order."""
        from forome.gem.umls import adjudicate_ui as A
        axes = [e for e in A.load_state()["entries"] if e["kind"] == "axis"]
        self.assertTrue(all(e["tier_explicit"] for e in axes),
                        [e["dimension"] for e in axes if not e["tier_explicit"]])
        core = [e["dimension"] for e in axes if e["tier"] == "core"]
        self.assertEqual(core[:6], ["knowledge_domain", "method", "target_type",
                                    "resolution", "credibility", "phenotype_scale"])
        cond = [e for e in axes if e["tier"] == "conditional"]
        self.assertTrue(all(e["activation"] for e in cond),
                        [e["dimension"] for e in cond if not e["activation"]])
        # core listed before every conditional
        order = [e["tier"] for e in axes]
        self.assertEqual(order, sorted(order, key=["core", "conditional",
                                                   "candidate"].index))


if __name__ == "__main__":
    unittest.main(verbosity=2)
