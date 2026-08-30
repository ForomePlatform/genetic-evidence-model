"""Regression tests for the review fixes on the sweep / rationale / local index."""
from __future__ import annotations

import unittest

from forome.gem.umls import sweep as S
from forome.gem.umls import adjudicate_ui as A
from forome.gem.umls import local_umls as L


class _Client:
    """search() returns canned hits per (term, semantic_types)."""
    version = "current"

    def __init__(self):
        self.calls = []

    def search(self, term, search_type="words", sabs=None, page_size=200,
               semantic_types=None, partial=False):
        self.calls.append((term, search_type, semantic_types, partial))
        if semantic_types == "T080" and term == "high":
            return [{"cui": "C1", "name": "High", "root_source": "SNOMEDCT_US",
                     "semantic_types": ["Qualitative Concept"]}]
        if semantic_types is None and term == "high":
            return [{"cui": "C1", "name": "High", "root_source": "SNOMEDCT_US",
                     "semantic_types": ["Qualitative Concept"]},
                    {"cui": "C2", "name": "High risk", "root_source": "NCI",
                     "semantic_types": ["Finding"]}]
        return []

    def atoms(self, cui):
        return [{"sab": s, "language": "ENG"} for s in ("MSH", "CHV", "SNOMEDCT_US", "RCD")]


def _protocol(sty_body):
    return {"name": "t", "dimension": "credibility", "tokens": ["HIGH"],
            "date_registered": "2026-08-30",
            "criteria": {c: c for c in S.CRITERIA},
            "sabs_of_interest": ["MSH", "SNOMEDCT_US"],
            "passes": {"string": {"terms": ["high"], "match": ["words"], "scopes": ["all"]},
                       "sty": sty_body}}


class TestStyTermsMode(unittest.TestCase):
    def test_terms_within_types_runs_on_any_client(self):
        p = _protocol({"mode": "terms", "terms_from": "string", "tuis": ["T080", "T033"]})
        S.validate_protocol(p)
        c = _Client()
        res = S.run(p, c)
        sty = next(r for r in res["passes"] if r["name"] == "sty")
        self.assertEqual(sty["status"], "executed")
        self.assertEqual(sty["mode"], "terms")
        self.assertEqual([q["scope"] for q in sty["queries"]], ["T080", "T033"])
        self.assertIn(("high", "words", "T080", False), c.calls)
        c1 = next(x for x in res["candidates"] if x["cui"] == "C1")
        self.assertEqual({f["pass"] for f in c1["found_by"]}, {"string", "sty"})

    def test_enumerate_mode_still_skips_without_local_index(self):
        p = _protocol({"tuis": ["T080"]})          # no terms -> enumerate
        S.validate_protocol(p)
        sty = next(r for r in S.run(p, _Client())["passes"] if r["name"] == "sty")
        self.assertEqual(sty["status"], "skipped")

    def test_enumerate_mode_is_capped_and_marks_truncation(self):
        class Local(_Client):
            def concepts_by_tui(self, tuis, limit=None):
                n = limit or 10_000
                return [{"cui": f"C{i}", "name": f"n{i}", "root_source": "MSH",
                         "semantic_types": ["Finding"]} for i in range(n)]
        p = _protocol({"tuis": ["T033"], "limit": 25})
        sty = next(r for r in S.run(p, Local())["passes"] if r["name"] == "sty")
        self.assertEqual(sty["queries"][0]["hits"], 25)
        self.assertEqual(sty["queries"][0]["truncated"], 25)

    def test_scalar_match_is_a_clear_error(self):
        p = _protocol({"mode": "terms", "terms": ["x"], "tuis": ["T080"]})
        p["passes"]["string"]["match"] = "words"
        with self.assertRaisesRegex(S.ProtocolError, "'match' must be a list"):
            S.validate_protocol(p)

    def test_enrich_filters_to_sabs_of_interest(self):
        p = _protocol({"mode": "terms", "terms": ["high"], "tuis": ["T080"]})
        res = S.run(p, _Client(), enrich=True)
        c1 = next(x for x in res["candidates"] if x["cui"] == "C1")
        self.assertEqual(c1["sabs"], ["MSH", "SNOMEDCT_US"])   # protocol order
        self.assertEqual(c1["sabs_other"], 2)
        tex = S.render_tex(res)
        self.assertIn("+2", tex)
        self.assertIn("p{2.6cm}", tex)                            # Source column breakable


class TestRationaleCaps(unittest.TestCase):
    def test_over_long_rejected_list_is_refused_not_trimmed(self):
        rows = [{"cui": f"C{i:07d}", "fails": "A"} for i in range(A.RATIONALE_MAXITEMS + 1)]
        with self.assertRaisesRegex(ValueError, "at most"):
            A.validate_rationale("unmapped", {"rejected": rows})
        ok = A.validate_rationale("unmapped", {"rejected": rows[:3]})
        self.assertEqual(len(ok["rejected"]), 3)

    def test_normalized_string_is_a_recordable_match(self):
        self.assertIn("normalizedString", A.MATCH_TYPES)
        self.assertIn("normalizedString", S.MATCH_TYPES)
        out = A.validate_rationale("unmapped", {"protocol": {"match": ["normalizedString"]}})
        self.assertEqual(out["protocol"]["match"], ["normalizedString"])


class TestDescendSearch(unittest.TestCase):
    class Tree:
        """A -> B,C; B -> D; C -> B (diamond); D -> leaf."""
        calls = 0
        def source_children(self, sab, code, page_size=120):
            type(self).calls += 1
            kids = {"A": [{"code": "B", "name": "Comparative Biology", "sab": sab},
                          {"code": "C", "name": "Zoology", "sab": sab}],
                    "B": [{"code": "D", "name": "Comparative Genomics", "sab": sab}],
                    "C": [{"code": "B", "name": "Comparative Biology", "sab": sab}]}
            return kids.get(code, [])

    def test_ranked_bfs_with_cycle_guard(self):
        rows = A.descend_search(self.Tree(), "NCI", "A", "comparative biology")
        names = [r["name"] for r in rows]
        self.assertEqual(names[0], "Comparative Biology")     # best score first
        self.assertEqual(names.count("Comparative Biology"), 1)  # diamond deduped
        self.assertIn("Comparative Genomics", names)          # depth 2 reached
        d = {r["name"]: r["depth"] for r in rows}
        self.assertEqual(d["Comparative Biology"], 1)
        self.assertEqual(d["Comparative Genomics"], 2)
        self.assertGreater(rows[0]["score"], rows[-1]["score"])

    def test_depth_and_breadth_caps(self):
        class Deep:
            def source_children(self, sab, code, page_size=120):
                n = int(code)
                return [{"code": str(n + 1), "name": f"n{n+1}", "sab": sab}]
        rows = A.descend_search(Deep(), "X", "0", "n", depth=2, limit=50)
        self.assertEqual(max(r["depth"] for r in rows), 2)


class TestExpandSearch(unittest.TestCase):
    class Cli:
        def search(self, term, search_type="words", sabs=None, page_size=200,
                   semantic_types=None, partial=False):
            if search_type == "exact" and term == "organism":
                return [{"cui": "C-ORG", "name": "Organism", "root_source": "SNOMEDCT_US",
                         "semantic_types": ["Organism"]}]
            if search_type == "words" and term.lower() in ("model animal",):
                return [{"cui": "C0599779", "name": "Animal Model", "root_source": "MTH",
                         "semantic_types": ["Animal"]}]
            return []
        def atoms(self, cui):
            return [{"sab": "SNOMEDCT_US", "code": "410607006", "language": "ENG"}]
        def source_children(self, sab, code, page_size=120):
            # organism -> Eukaryota -> Animal (organism): the hit sits at
            # depth 2, and the FSN parenthetical must be stripped
            if code == "410607006":
                return [{"code": "EUK", "name": "Eukaryota", "sab": sab}]
            if code == "EUK":
                return [{"code": "387961004", "name": "Animal (organism)", "sab": sab},
                        {"code": "x", "name": "Plant", "sab": sab}]
            return []
        def source_ancestors(self, sab, code, page_size=120):
            return [{"code": "ROOT", "name": "SNOMED CT Concept", "sab": sab}]

    def test_model_organism_finds_animal_model(self):
        out = A.expand_search(self.Cli(), "model organism")
        hit = next((r for r in out["results"] if r["cui"] == "C0599779"), None)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["via"], "organism → Animal")
        self.assertEqual(hit["variant"].lower(), "model animal")
        # ancestors (SNOMED CT Concept) must NOT be substituted
        self.assertFalse(any("SNOMED" in (r["via"] or "") for r in out["results"]))
        self.assertGreaterEqual(out["n_variants"], 3)   # Eukaryota, Animal, Plant

    def test_no_pivot_words_is_empty_not_error(self):
        class Empty(self.Cli):
            def search(self, term, **k): return []
        out = A.expand_search(Empty(), "xyzzy blorp")
        self.assertEqual(out["results"], [])


class TestHybridClient(unittest.TestCase):
    def test_routing_pg_for_search_uts_for_details(self):
        class PG:
            def search(self, *a, **k): return ["pg-search"]
            def atoms(self, c): return ["pg-atoms"]
            def concepts_by_tui(self, t, limit=None): return ["pg-tui"]
            def release(self): return {"version": "2026AA"}
            def sources(self): return [{"sab": "MSH"}]
        class UTS:
            def relations(self, c): return ["uts-rel"]
            def definitions(self, c): return ["uts-def"]
            def get_concept(self, c): return {"cui": c}
            def rollup(self, *a, **k): return ["uts-roll"]
            def sources(self): return [{"sab": "MSH", "name": "MeSH"}]
        h = A.HybridClient(PG(), UTS())
        self.assertEqual(h.search("x"), ["pg-search"])
        self.assertEqual(h.atoms("C1"), ["pg-atoms"])
        self.assertEqual(h.concepts_by_tui("T090"), ["pg-tui"])
        self.assertEqual(h.relations("C1"), ["uts-rel"])
        self.assertEqual(h.rollup("C1"), ["uts-roll"])
        self.assertEqual(h.sources()[0]["name"], "MeSH")   # UTS names preferred
        self.assertEqual(h.release()["version"], "2026AA")

    def test_state_carries_search_backend(self):
        st = A.load_state()
        self.assertIn("search_backend", st)


class TestNeedsFollowDecisions(unittest.TestCase):
    """Review flags must follow in-session decisions, not only the last Rebuild."""
    def test_live_decision_overrides_snapshot(self):
        base = {"kind": "value", "status": "review", "curated": False}
        self.assertEqual(A.entry_needs({**base, "decision": "accept"}), [])
        self.assertEqual(A.entry_needs({**base, "decision": "unmapped"}), ["no-rationale"])
        self.assertEqual(A.entry_needs({**base, "decision": "unmapped",
                                        "protocol": {"queries": ["x"]}}), [])
        # cleared since the last Rebuild: the snapshot's curated flag is stale
        self.assertEqual(A.entry_needs({"kind": "value", "status": "mapped",
                                        "curated": True, "decision": None}), ["unconfirmed"])
        # an accepted CUI the harness could not confirm stays in review
        self.assertEqual(A.entry_needs({**base, "decision": "accept", "error": "x"}), ["review"])


class TestLocalIndexFixes(unittest.TestCase):
    def test_concepts_by_tui_sql_selects_root_source(self):
        sql, params = L.build_concepts_by_tui_sql(["T080"], limit=5)
        self.assertIn("p.sab AS root_source", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(params, [["T080"], 5])

    def test_sty_backfill_sql(self):
        sql, params = L.build_sty_backfill_sql([{"tui": "T080", "name": "Qualitative Concept",
                                                 "tree_number": "A2.1.2"}, {"name": "no tui"}])
        self.assertIn("UPDATE mrsty AS s SET sty = v.name, stn = v.stn", sql)
        self.assertIn("(s.sty IS NULL OR s.sty = '')", sql)
        self.assertEqual(params, ["T080", "Qualitative Concept", "A2.1.2"])
        self.assertEqual(L.build_sty_backfill_sql([])[0], "SELECT 0")

    def test_query_wraps_pre_statements_in_one_transaction(self):
        events = []

        class Cur:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            description = [("x",)]
            def execute(self, sql, params=None): events.append(("exec", sql[:20]))
            def fetchall(self): return []

        class Tx:
            def __enter__(self): events.append(("begin",))
            def __exit__(self, *a): events.append(("commit",)); return False

        class Conn:
            def cursor(self): return Cur()
            def transaction(self): return Tx()

        c = L.PgUMLSClient.__new__(L.PgUMLSClient)
        c._conn = Conn(); c.dsn = None; c.lang = "ENG"; c.min_similarity = 0.3
        c._query("SELECT 1", [], pre=[("SELECT set_config", [])])
        self.assertEqual(events[0], ("begin",))
        self.assertEqual(events[-1], ("commit",))
        self.assertEqual([e for e in events if e[0] == "exec"],
                         [("exec", "SELECT set_config"), ("exec", "SELECT 1")])


if __name__ == "__main__":
    unittest.main()
