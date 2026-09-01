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
        doc = H.build(FixtureClient(FIXTURES), live=True, adjudications={})
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
        doc = H.build(FixtureClient(FIXTURES), live=True, adjudications={})
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
        part = H.build(FixtureClient(FIXTURES), live=True, adjudications={}, only_dims={"method"})
        self.assertTrue(part["entries"])
        self.assertEqual({e["dimension"] for e in part["entries"]}, {"method"})
        full = H.build(FixtureClient(FIXTURES), live=True, adjudications={})
        want = [e for e in full["entries"] if e["dimension"] == "method"]
        self.assertEqual(part["entries"], want)
        counts = part["meta"]["counts"]
        self.assertEqual(sum(counts[s] for s in
                             ("mapped", "review", "unmapped", "pending")),
                         len(part["entries"]))

    def test_render_produces_valid_latex(self):
        doc = H.build(FixtureClient(FIXTURES), live=True, adjudications={})
        with tempfile.TemporaryDirectory() as d:
            cw = Path(d) / "cw.yaml"
            import yaml
            cw.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
            out = R.render(cw, R.DEFAULT_OMOP)
        self.assertIn(r"\section{UMLS crosswalk and illustrative OMOP CDM positioning}", out)
        self.assertEqual(out.count(r"\begin{longtable}"),
                         out.count(r"\end{longtable}"))
        self.assertEqual(out.count(r"\begin{longtable}"), 2)
        self.assertIn("C9000001", out)            # mapped CUI rendered
        self.assertIn("OMOP CDM", out)            # OMOP section present

    def test_render_escapes_special_chars(self):
        self.assertEqual(R.tex("a_b & c% {d}"), r"a\_b \& c\% \{d\}")

    def test_render_relation_column_and_argued_gap(self):
        """The relation column comes from the adjudications overlay, and an
        unmapped verdict that carries a rationale renders as an argued gap,
        distinct from an unresolved one."""
        import yaml
        doc = H.build(FixtureClient(FIXTURES), live=True, adjudications={})
        vals = [e for e in doc["entries"] if e["kind"] != "axis"]
        mapped = next(e for e in vals if e["status"] == "mapped")
        gap, unresolved = vals[-1], vals[-2]
        gap["status"] = unresolved["status"] = "unmapped"
        gap["cui"] = unresolved["cui"] = None
        adj = {H._adj_key(mapped["dimension"], mapped["token"]):
                   {"accept": mapped["cui"], "relation": "close", "note": "t"},
               H._adj_key(gap["dimension"], gap["token"]):
                   {"unmapped": True, "relation": "none", "note": "t",
                    "rejected": [{"cui": "C0000009", "fails": "A", "why": "x"}]}}
        with tempfile.TemporaryDirectory() as d:
            cw, aj = Path(d) / "cw.yaml", Path(d) / "adj.yaml"
            cw.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
            aj.write_text(yaml.safe_dump({"adjudications": adj}))
            out = R.render(cw, R.DEFAULT_OMOP, aj)
        self.assertIn("& Relation &", out)
        row = next(l for l in out.splitlines()
                   if l.startswith(rf"\quad {R.tex(mapped['token'])} &"))
        self.assertIn("& close &", row)
        gap_row = next(l for l in out.splitlines()
                       if l.startswith(rf"\quad {R.tex(gap['token'])} &"))
        self.assertIn("argued gap (1 rejected near-miss)", gap_row)
        self.assertIn(r"\emph{none}", gap_row)
        unr_row = next(l for l in out.splitlines()
                       if l.startswith(rf"\quad {R.tex(unresolved['token'])} &"))
        self.assertIn("unresolved", unr_row)
        self.assertIn(r"\Cref{sec:supp-crosswalk}", out)   # s15's real label


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

    def test_preferences_and_comment_preserving_writes(self):
        """Preferred vocabularies resolve value hint > dimension override >
        workspace list, and app writes keep the inventory's comments."""
        import shutil
        from forome.gem.umls import adjudicate_ui as A
        ws = Path(tempfile.mkdtemp()) / "mapping"
        ws.mkdir()
        shutil.copy(DATA_DIR / "dimensions_inventory.yaml", ws / "dimensions_inventory.yaml")
        shutil.copy(DATA_DIR / "umls_crosswalk.yaml", ws / "umls_crosswalk.yaml")
        saved = (A.CROSSWALK, H.INVENTORY, H.ADJUDICATIONS)
        try:
            A.CROSSWALK = ws / "umls_crosswalk.yaml"
            H.INVENTORY = ws / "dimensions_inventory.yaml"
            H.ADJUDICATIONS = ws / "adjudications.yaml"
            comments_before = sum(1 for l in H.INVENTORY.read_text().splitlines()
                                  if l.lstrip().startswith("#"))
            self.assertGreater(comments_before, 20)

            self.assertEqual(A.save_prefs("snomedct_us, MSH, msh, NCI"),
                             ["SNOMEDCT_US", "MSH", "NCI"])
            A.save_axis("method", preferred_sabs=["NCI"])       # dimension override
            st = A.load_state()
            by = {(e["dimension"], e["token"]): e for e in st["entries"]}
            self.assertEqual(st["prefs"]["workspace"], ["SNOMEDCT_US", "MSH", "NCI"])
            # GWAS has its own sab: MSH hint -> first; then dim override; then ws
            self.assertEqual(by[("method", "GWAS")]["sab_prefs"],
                             ["MSH", "NCI", "SNOMEDCT_US"])
            # credibility HIGH has no hint and no override -> workspace order
            self.assertEqual(by[("credibility", "HIGH")]["sab_prefs"],
                             ["SNOMEDCT_US", "MSH", "NCI"])
            axis = by[("method", None)]
            self.assertEqual(axis["preferred_sabs"], ["NCI"])

            # comments survived two app writes; the axis type is intact
            comments_after = sum(1 for l in H.INVENTORY.read_text().splitlines()
                                 if l.lstrip().startswith("#"))
            self.assertEqual(comments_after, comments_before)
            self.assertEqual(axis["sty_tui"], "T062")
            # clearing the override removes the key
            A.save_axis("method", preferred_sabs=[])
            e = next(x for x in A.load_state()["entries"]
                     if x["dimension"] == "method" and x["kind"] == "axis")
            self.assertEqual(e["preferred_sabs"], [])
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


class TestStructuredRationale(unittest.TestCase):
    """Structured 'unmapped' / 'accept' rationale (relation / rejected /
    protocol): validation, YAML round-trip in both file styles, exposure in
    load_state, and the /api/decide endpoint end to end -- always against a
    temp copy of the workspace, never the real adjudications.yaml."""

    RATIONALE = {
        "unmapped": True,
        "note": 'GEM-internal tier; has "double" quotes, it\'s got: colons # and hash',
        "relation": "none",
        "rejected": [
            {"cui": "C1234567", "name": "IPSS-R Risk Category, Low", "sab": "NCI",
             "fails": "D", "why": "an MDS prognostic bucket, not \"epistemic\" credibility"},
            {"cui": "C7654321", "name": "Low (qualifier)", "fails": "A",
             "why": "measurand degree: it's a quantity, [not] a credibility {tier}"},
        ],
        "protocol": {"queries": ["low credibility", "low: evidence"],
                     "scopes": ["axis", "all"], "match": ["words", "partial"],
                     "sabs": ["MSH", "NCI"], "umls": "UTS current, queried 2026-08-30"},
    }

    def _ws(self, copy_data=False):
        import shutil
        from forome.gem.umls import adjudicate_ui as A
        ws = Path(tempfile.mkdtemp()) / "mapping"
        ws.mkdir()
        if copy_data:
            shutil.copy(DATA_DIR / "dimensions_inventory.yaml", ws / "dimensions_inventory.yaml")
            shutil.copy(DATA_DIR / "umls_crosswalk.yaml", ws / "umls_crosswalk.yaml")
        saved = (A.CROSSWALK, H.INVENTORY, H.ADJUDICATIONS)
        A.CROSSWALK = ws / "umls_crosswalk.yaml"
        H.INVENTORY = ws / "dimensions_inventory.yaml"
        H.ADJUDICATIONS = ws / "adjudications.yaml"
        self.addCleanup(lambda: setattr(A, "CROSSWALK", saved[0]))
        self.addCleanup(lambda: setattr(H, "INVENTORY", saved[1]))
        self.addCleanup(lambda: setattr(H, "ADJUDICATIONS", saved[2]))
        return ws

    def test_write_roundtrip_block_and_compact_styles(self):
        from forome.gem.umls import adjudicate_ui as A
        self._ws()
        adj = {"credibility/LOW": dict(self.RATIONALE),
               "method/GWAS": {"accept": "C9000001",
                               "note": 'plain "quoted" note: with colon'},
               "resolution/(axis)": {"accept_sty": "T082", "note": "axis"}}
        A.write_adjudications(adj)
        text = H.ADJUDICATIONS.read_text()
        lines = text.splitlines()
        # header comments kept, verbatim
        self.assertEqual(lines[:len(A.ADJ_HEADER)], A.ADJ_HEADER)
        # entries WITHOUT rationale stay one compact flow-style line each
        gwas = [l for l in lines if l.startswith('  "method/GWAS":')]
        self.assertEqual(len(gwas), 1)
        self.assertIn("{accept: C9000001, note:", gwas[0])
        axis = [l for l in lines if l.startswith('  "resolution/(axis)":')]
        self.assertIn("{accept_sty: T082, note:", axis[0])
        # the rationale entry is a block mapping under its quoted key
        i = lines.index('  "credibility/LOW":')
        self.assertTrue(lines[i + 1].startswith("    unmapped: true"))
        self.assertTrue(any(l.startswith("    rejected:") for l in lines[i:]))
        self.assertTrue(any(l.startswith("    protocol:") for l in lines[i:]))
        # everything round-trips through the harness loader, quotes included
        back = H.load_adjudications(H.ADJUDICATIONS)
        self.assertEqual(back, adj)
        self.assertEqual(back["credibility/LOW"]["rejected"][1]["why"],
                         "measurand degree: it's a quantity, [not] a credibility {tier}")
        # the harness treats the block entry like any unmapped adjudication
        r = H.apply_adjudication({"dimension": "credibility", "token": "LOW",
                                  "status": "review", "candidates": []},
                                 back["credibility/LOW"])
        self.assertEqual(r["status"], "unmapped")
        self.assertTrue(r["curated"])

    def test_validate_rationale(self):
        from forome.gem.umls import adjudicate_ui as A
        V = A.validate_rationale
        # nothing given -> nothing stored (compact line preserved)
        self.assertEqual(V("accept", {"cui": "C1"}), {})
        self.assertEqual(V("unmapped", {}), {})
        # accept: relation from the allowed set, never 'none'
        self.assertEqual(V("accept", {"relation": "broader"}), {"relation": "broader"})
        with self.assertRaises(ValueError):
            V("accept", {"relation": "none"})
        with self.assertRaises(ValueError):
            V("accept", {"relation": "identical"})
        # unmapped: relation is none (defaulted when a rationale is given)
        out = V("unmapped", {"rejected": [{"cui": "C1", "fails": "b", "why": "x" * 400,
                                          "name": "N", "sab": "msh"}],
                             "protocol": {"queries": ["q", "", "q"], "scopes": ["axis"],
                                          "match": ["words"], "sabs": ["msh"],
                                          "umls": "u", "bogus": "dropped"}})
        self.assertEqual(out["relation"], "none")
        row = out["rejected"][0]
        self.assertEqual((row["cui"], row["fails"], row["name"], row["sab"]),
                         ("C1", "B", "N", "msh"))
        self.assertEqual(len(row["why"]), A.RATIONALE_MAXLEN)     # capped
        self.assertEqual(out["protocol"], {"queries": ["q"], "scopes": ["axis"],
                                           "match": ["words"], "sabs": ["MSH"],
                                           "umls": "u"})
        with self.assertRaises(ValueError):
            V("unmapped", {"relation": "exact"})
        for bad in ({"rejected": "C1"},                       # not a list
                    {"rejected": [{"fails": "A"}]},           # no cui
                    {"rejected": [{"cui": "C 1", "fails": "A"}]},   # bad cui shape
                    {"rejected": [{"cui": "C1"}]},            # no criterion
                    {"rejected": [{"cui": "C1", "fails": "E"}]},
                    {"rejected": ["C1"]},
                    {"protocol": []},
                    {"protocol": {"scopes": ["everywhere"]}},
                    {"protocol": {"match": ["fuzzy"]}},
                    {"protocol": {"queries": "q"}}):
            with self.assertRaises(ValueError, msg=repr(bad)):
                V("unmapped", bad)

    def test_load_state_exposes_rationale(self):
        from forome.gem.umls import adjudicate_ui as A
        self._ws(copy_data=True)
        A.write_adjudications({"credibility/LOW": dict(self.RATIONALE),
                               "method/GWAS": {"accept": "C9000001", "note": "n",
                                               "relation": "close"}})
        by = {(e["dimension"], e["token"]): e for e in A.load_state()["entries"]}
        low = by[("credibility", "LOW")]
        self.assertEqual(low["decision"], "unmapped")
        self.assertEqual(low["relation"], "none")
        self.assertEqual([r["cui"] for r in low["rejected"]], ["C1234567", "C7654321"])
        self.assertEqual(low["protocol"]["scopes"], ["axis", "all"])
        gwas = by[("method", "GWAS")]
        self.assertEqual(gwas["relation"], "close")
        self.assertEqual((gwas["rejected"], gwas["protocol"]), ([], {}))
        # an entry with no adjudication at all: None / [] / {}
        other = by[("credibility", "HIGH")]
        self.assertIsNone(other["relation"])
        self.assertEqual((other["rejected"], other["protocol"]), ([], {}))
        # axis entries carry the keys too
        self.assertEqual((by[("method", None)]["rejected"], by[("method", None)]["protocol"]), ([], {}))

    def test_decide_endpoint_stores_validates_and_clears(self):
        import json
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        from forome.gem.umls import adjudicate_ui as A
        self._ws()
        # an ephemeral port: never the user's 8765, and immune to collisions
        srv = ThreadingHTTPServer(("127.0.0.1", 0), A.Handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        url = f"http://127.0.0.1:{srv.server_address[1]}/api/decide"

        def post(body):
            req = Request(url, data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
            try:
                with urlopen(req) as r:
                    return r.status, json.loads(r.read())
            except HTTPError as ex:
                return ex.code, json.loads(ex.read())

        # accept with a relation
        code, j = post({"key": "method/GWAS", "verdict": "accept", "cui": "C9000001",
                        "relation": "close", "note": "near enough"})
        self.assertEqual((code, j), (200, {"ok": True}))
        # unmapped with the full argument
        code, j = post({"key": "credibility/LOW", "verdict": "unmapped",
                        "note": self.RATIONALE["note"],
                        "rejected": self.RATIONALE["rejected"],
                        "protocol": self.RATIONALE["protocol"]})
        self.assertEqual(code, 200, j)
        adj = H.load_adjudications(H.ADJUDICATIONS)
        self.assertEqual(adj["method/GWAS"],
                         {"accept": "C9000001", "note": "near enough", "relation": "close"})
        self.assertEqual(adj["credibility/LOW"], self.RATIONALE)   # relation defaulted to none
        # validation errors are 400s and leave the file untouched
        for bad in ({"key": "credibility/LOW", "verdict": "unmapped", "relation": "exact"},
                    {"key": "credibility/LOW", "verdict": "unmapped",
                     "rejected": [{"cui": "C1", "fails": "Z"}]},
                    {"key": "method/GWAS", "verdict": "accept", "cui": "C9000001",
                     "relation": "none"},
                    {"key": "method/GWAS", "verdict": "accept", "cui": "not a cui"},
                    {"key": "method/GWAS", "verdict": "maybe"}):
            code, j = post(bad)
            self.assertEqual(code, 400, bad)
            self.assertIn("error", j)
        self.assertEqual(H.load_adjudications(H.ADJUDICATIONS), adj)
        # clear removes the decision AND its rationale
        code, _ = post({"key": "credibility/LOW", "verdict": "clear"})
        self.assertEqual(code, 200)
        self.assertNotIn("credibility/LOW", H.load_adjudications(H.ADJUDICATIONS))

    def test_embedded_js_parses(self):
        """The Mapping Studio's inline script must at least parse (node --check)."""
        import re
        import shutil
        import subprocess
        from forome.gem.umls import adjudicate_ui as A
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        js = A.HTML.split("<script>\n", 1)[1].split("\n</script></body></html>")[0]
        self.assertIn("function openUnmapped", js)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(js)
        r = subprocess.run([node, "--check", fh.name], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        # the criteria offered to the curator are the shared ones
        for k in A.CRITERIA:
            self.assertRegex(js, rf"\b{k}:\"")
        # the worklist machinery is present and data-driven: the JS reads
        # entry.needs / STATE.needs and never re-derives the definition
        for fn in ("function worklist", "function wlFiltered", "function nextNeeding",
                   "function needChips", "function wireWorklist", "function openEntry"):
            self.assertIn(fn, js)
        self.assertIn("e.needs||[]", js)
        self.assertNotIn("x.status==='review'||!x.curated", js)
        self.assertNotIn("e.status==='review'||!e.curated", js)


class TestNeeds(unittest.TestCase):
    """ONE server-side definition of 'what still needs a curator's eyes'
    (adjudicate_ui.entry_needs, exposed by load_state as entries[].needs,
    state.needs / need_codes / need_labels / counts.needs) -- every code, the
    no-flag cases, totals and order -- against a synthetic temp workspace."""

    def _ws(self):
        from forome.gem.umls import adjudicate_ui as A
        ws = Path(tempfile.mkdtemp()) / "mapping"
        ws.mkdir()
        saved = (A.CROSSWALK, H.INVENTORY, H.ADJUDICATIONS)
        A.CROSSWALK = ws / "umls_crosswalk.yaml"
        H.INVENTORY = ws / "dimensions_inventory.yaml"
        H.ADJUDICATIONS = ws / "adjudications.yaml"
        self.addCleanup(lambda: setattr(A, "CROSSWALK", saved[0]))
        self.addCleanup(lambda: setattr(H, "INVENTORY", saved[1]))
        self.addCleanup(lambda: setattr(H, "ADJUDICATIONS", saved[2]))
        return ws

    def _populate(self, ws):
        """Three dimensions: 'typed' (axis T062) with one value per case,
        'untyped' (no semantic type, one value), 'flag' (no type, no values)."""
        import yaml
        from forome.gem.umls import adjudicate_ui as A
        inv = {"dimensions": {
            "typed": {"tier": "core", "order": 10,
                      "axis": {"query": "Methods", "semantic_type": "T062"}},
            "untyped": {"tier": "core", "order": 20, "axis": {"query": "Whatever"}},
            "flag": {"tier": "core", "order": 30, "axis": {"query": "Boolean"}},
        }}
        (ws / "dimensions_inventory.yaml").write_text(yaml.safe_dump(inv, sort_keys=False))

        def val(dim, tok, status, curated=False, cui=None):
            e = {"dimension": dim, "token": tok, "kind": "value", "query": tok.lower(),
                 "status": status, "curated": curated, "candidates": []}
            if cui:
                e.update(cui=cui, matched_name=tok.title(), root_source="MSH")
            return e
        cw = {"entries": [
            val("typed", "CONFIRMED", "mapped", True, "C9000001"),   # nothing to do
            val("typed", "AUTO", "mapped", False, "C9000002"),       # unconfirmed
            val("typed", "PENDING_REVIEW", "review"),                # review
            val("typed", "NOTHING_FOUND", "unmapped"),               # unresolved
            val("typed", "BARE_VERDICT", "unmapped", True),          # no-rationale
            val("typed", "ARGUED", "unmapped", True),                # nothing to do
            val("untyped", "X", "mapped", False, "C9000003"),        # unconfirmed
        ]}
        (ws / "umls_crosswalk.yaml").write_text(yaml.safe_dump(cw, sort_keys=False))
        A.write_adjudications({
            "typed/CONFIRMED": {"accept": "C9000001", "note": "yes"},
            "typed/BARE_VERDICT": {"unmapped": True, "note": "no argument recorded"},
            "typed/ARGUED": {"unmapped": True, "note": "", "relation": "none",
                             "rejected": [{"cui": "C9000009", "fails": "A",
                                           "why": "denotes something else"}]},
        })

    def test_need_codes_per_case(self):
        from forome.gem.umls import adjudicate_ui as A
        self._populate(self._ws())
        st = A.load_state()
        by = {(e["dimension"], e["token"]): e["needs"] for e in st["entries"]}
        self.assertEqual(by[("typed", "CONFIRMED")], [])
        self.assertEqual(by[("typed", "AUTO")], ["unconfirmed"])
        self.assertEqual(by[("typed", "PENDING_REVIEW")], ["review"])
        self.assertEqual(by[("typed", "NOTHING_FOUND")], ["unresolved"])
        self.assertEqual(by[("typed", "BARE_VERDICT")], ["no-rationale"])
        self.assertEqual(by[("typed", "ARGUED")], [])
        self.assertEqual(by[("untyped", "X")], ["unconfirmed"])
        # axes: flagged only when untyped AND there are values to search
        self.assertEqual(by[("typed", None)], [])
        self.assertEqual(by[("untyped", None)], ["untyped"])
        self.assertEqual(by[("flag", None)], [])
        # every entry carries the key (empty list = nothing to do)
        self.assertTrue(all(isinstance(e["needs"], list) for e in st["entries"]))

    def test_totals_labels_and_worklist_order(self):
        import json
        from forome.gem.umls import adjudicate_ui as A
        self._populate(self._ws())
        st = A.load_state()
        self.assertEqual(st["needs"], {"review": 1, "unconfirmed": 2, "unresolved": 1,
                                       "no-rationale": 1, "untyped": 1})
        self.assertEqual(st["counts"]["needs"], 6)
        # the fixed order is the server's, exposed for the UI as data
        codes = [c[0] for c in A.NEED_CODES]
        self.assertEqual(st["need_codes"], codes)
        self.assertEqual(list(st["needs"]), codes)
        self.assertEqual(set(st["need_labels"]), set(codes))
        for c in codes:
            lab = st["need_labels"][c]
            self.assertTrue(lab["label"] and lab["desc"], c)
            self.assertIn(lab["scope"], ("value", "axis"))
        self.assertEqual(st["need_labels"]["untyped"]["scope"], "axis")
        self.assertEqual(st["need_labels"]["no-rationale"]["desc"],
                         "recorded as unmapped without an argument")
        # worklist order = entries order: dimension order, axis before its values
        self.assertEqual([e["key"] for e in st["entries"] if e["needs"]],
                         ["typed/AUTO", "typed/PENDING_REVIEW", "typed/NOTHING_FOUND",
                          "typed/BARE_VERDICT", "untyped/(axis)", "untyped/X"])
        json.dumps(st)   # what /api/state serves

    def test_entry_needs_edge_cases(self):
        from forome.gem.umls import adjudicate_ui as A
        N = A.entry_needs
        self.assertEqual(N({"kind": "value", "status": "pending"}), [])      # not live
        self.assertEqual(N({"kind": "value", "status": "review", "curated": True}), ["review"])
        self.assertEqual(N({"kind": "axis", "sty_tui": None}, dim_has_values=False), [])
        self.assertEqual(N({"kind": "axis", "sty_tui": None}, dim_has_values=True), ["untyped"])
        self.assertEqual(N({"kind": "axis", "sty_tui": "T062"}, dim_has_values=True), [])
        # a protocol alone (the modal's shape when nothing was seen) is an argument
        self.assertEqual(N({"kind": "value", "status": "unmapped", "curated": True,
                            "rejected": [], "protocol": {"queries": ["q"]}}), [])
        self.assertEqual(N({"kind": "value", "status": "unmapped", "curated": True,
                            "rejected": [], "protocol": {}}), ["no-rationale"])

    def test_no_rationale_clears_once_argued(self):
        from forome.gem.umls import adjudicate_ui as A
        self._populate(self._ws())
        adj = H.load_adjudications(H.ADJUDICATIONS)
        adj["typed/BARE_VERDICT"] = {"unmapped": True, "note": "", "relation": "none",
                                     "rejected": [],
                                     "protocol": {"queries": ["bare verdict"],
                                                  "scopes": ["axis"], "umls": "UTS current"}}
        A.write_adjudications(adj)
        st = A.load_state()
        bare = next(e for e in st["entries"] if e["key"] == "typed/BARE_VERDICT")
        self.assertEqual(bare["needs"], [])
        self.assertEqual(st["needs"]["no-rationale"], 0)
        self.assertEqual(st["counts"]["needs"], 5)

    def test_repo_workspace_state_is_consistent(self):
        """Against the repo's own data (read-only): totals agree with the
        per-entry lists, and axes are flagged only when they have values."""
        from forome.gem.umls import adjudicate_ui as A
        st = A.load_state()
        self.assertEqual(sum(st["needs"].values()),
                         sum(len(e["needs"]) for e in st["entries"]))
        self.assertEqual(st["counts"]["needs"], sum(1 for e in st["entries"] if e["needs"]))
        vals_of = {}
        for e in st["entries"]:
            if e["kind"] != "axis":
                vals_of[e["dimension"]] = vals_of.get(e["dimension"], 0) + 1
        for e in st["entries"]:
            if e["kind"] == "axis":
                self.assertEqual("untyped" in e["needs"],
                                 not e["sty_tui"] and vals_of.get(e["dimension"], 0) > 0,
                                 e["dimension"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
