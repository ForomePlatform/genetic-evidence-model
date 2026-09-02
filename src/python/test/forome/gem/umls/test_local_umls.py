#!/usr/bin/env python3
"""Offline tests for the local PostgreSQL UMLS index (forome.gem.umls.local_umls).

No database and no psycopg: the RRF parser runs on a tiny fixture written to a
temp dir, the SQL builders are checked as pure functions, the loader's
``--dry-run`` runs in-process, and the DB-touching loader / client paths are
exercised against fakes (a fake ``psycopg`` module in ``sys.modules`` and a
fake connection injected into ``PgUMLSClient``).
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path

from forome.gem.umls import local_umls as L

# A tiny synthetic MRCONSO: 18 fields + trailing pipe. Synthetic CUIs only.
MRCONSO_LINES = [
    "C9000001|ENG|P|L0000001|PF|S0000001|Y|A0000001||M0000001||MSH|MH|D000001|Gene Locus|0|N|256|",
    "C9000001|ENG|S|L0000002|VC|S0000002|Y|A0000002||||SNOMEDCT_US|SY|100001|Locus, Gene|9|N||",
    "C9000001|FRE|P|L0000003|PF|S0000003|Y|A0000003||||MSHFRE|MH|D000001|Locus génique|0|N||",
    "C9000002|ENG|P|L0000004|PF|S0000004|Y|A0000004||||NCI|PT|C12345|Genome-wide association study|0|N||",
    "C9000002|ENG|S|L0000005|VO|S0000005|N|A0000005||||NCI|SY|C12345|GWAS|0|O||",
    "C9000003|SPA|P|L0000006|PF|S0000006|Y|A0000006||||MSHSPA|MH|D000003|Genoma|0|N||",
]
MALFORMED = "C9000009|ENG|P|too|short|"          # 5 fields -> skipped
MRSTY_LINES = [
    "C9000001|T082|A2.1.5|Spatial Concept|AT00000001||",
    "C9000002|T062|B1.3.1.1|Research Activity|AT00000002||",
    "C9000003|T028|A1.2.3.5|Gene or Genome|AT00000003||",
]


def _write_fixture(d: Path) -> Path:
    lines = MRCONSO_LINES[:3] + [MALFORMED] + MRCONSO_LINES[3:]
    (d / "MRCONSO.RRF").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (d / "MRSTY.RRF").write_text("\n".join(MRSTY_LINES) + "\n", encoding="utf-8")
    return d


class TestIterRRF(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = _write_fixture(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_rows_fields_and_trailing_pipe(self):
        stats = {}
        with self.assertLogs(L.log, level="WARNING") as cm:
            rows = list(L.iter_rrf(self.dir / "MRCONSO.RRF", 18, stats))
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(len(r) == 18 for r in rows))
        self.assertEqual(rows[0][0], "C9000001")
        self.assertEqual(rows[0][14], "Gene Locus")
        self.assertEqual(rows[0][17], "256")          # last field (CVF) kept
        self.assertEqual(rows[1][17], "")             # empty trailing field kept as ''
        self.assertEqual(rows[2][14], "Locus génique")  # UTF-8 decoded
        self.assertEqual(stats, {"rows": 6, "skipped": 1})
        self.assertIn("expected 18 fields, got 5", cm.output[0])

    def test_mrsty_columns(self):
        rows = list(L.iter_rrf(self.dir / "MRSTY.RRF", len(L.MRSTY_COLUMNS)))
        self.assertEqual([r[1] for r in rows], ["T082", "T062", "T028"])
        self.assertEqual(rows[0][3], "Spatial Concept")

    def test_column_lists(self):
        self.assertEqual(len(L.MRCONSO_COLUMNS), 18)
        self.assertEqual(L.MRCONSO_COLUMNS[0], "CUI")
        self.assertEqual(L.MRCONSO_COLUMNS[-1], "CVF")
        self.assertEqual(L.MRCONSO_COLUMNS[14], "STR")
        self.assertEqual(L.MRSTY_COLUMNS, ["CUI", "TUI", "STN", "STY", "ATUI", "CVF"])

    def test_gzip_transparent(self):
        import gzip
        gz = self.dir / "MRSTY.RRF.gz"
        with gzip.open(gz, "wt", encoding="utf-8") as fh:
            fh.write("\n".join(MRSTY_LINES) + "\n")
        self.assertEqual(len(list(L.iter_rrf(gz, 6))), 3)


class TestSchemaSQL(unittest.TestCase):
    def test_tables(self):
        ddl = "\n".join(L.build_schema_sql())
        self.assertIn("CREATE TABLE IF NOT EXISTS mrconso", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS mrsty", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS umls_release", ddl)
        for col in ("cui", "lat", "sab", "tty", "code", "str", "suppress", "cvf"):
            self.assertIn(f"    {col} text", ddl)
        for col in ("version", "loaded_at", "source_dir", "rows_mrconso", "rows_mrsty"):
            self.assertIn(col, ddl)

    def test_indexes(self):
        idx = L.build_index_sql()
        self.assertEqual(idx[0], "CREATE EXTENSION IF NOT EXISTS pg_trgm")
        joined = "\n".join(idx)
        self.assertIn("ON mrconso USING btree (cui)", joined)
        self.assertIn("ON mrconso USING btree (sab)", joined)
        self.assertIn("(lower(str))", joined)
        self.assertIn("USING gin (to_tsvector('english', str))", joined)
        self.assertIn("USING gin (to_tsvector('simple', str))", joined)
        self.assertIn("USING gin (lower(str) gin_trgm_ops)", joined)
        self.assertIn("ON mrsty USING btree (cui)", joined)
        self.assertIn("ON mrsty USING btree (tui)", joined)
        # every index has a matching DROP for reloads
        drops = "\n".join(L.build_drop_index_sql())
        for name, _ in L.INDEXES:
            self.assertIn(f"DROP INDEX IF EXISTS {name}", drops)

    def test_copy_and_release_sql(self):
        self.assertEqual(
            L.build_copy_sql("mrsty", L.MRSTY_COLUMNS),
            "COPY mrsty (cui, tui, stn, sty, atui, cvf) FROM STDIN")
        self.assertTrue(L.build_copy_sql("mrconso", L.MRCONSO_COLUMNS)
                        .startswith("COPY mrconso (cui, lat, ts, lui, stt, sui, ispref, aui,"))
        self.assertIn("INSERT INTO umls_release", L.build_release_insert_sql())


class TestSearchSQL(unittest.TestCase):
    def test_exact(self):
        sql, params = L.build_search_sql("Gene Locus", "exact")
        self.assertIn("lower(m.str) = lower(%s)", sql)
        self.assertIn("m.lat = %s", sql)
        self.assertEqual(params, ["ENG", "Gene Locus", 200])
        self.assertIn("GROUP BY m.cui", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertIn("AS semantic_types", sql)
        self.assertIn("p.sab AS root_source", sql)
        self.assertNotIn("%%", sql)

    def test_words(self):
        sql, params = L.build_search_sql("gene locus", "words", page_size=50)
        self.assertIn("to_tsvector('english', m.str) @@ plainto_tsquery('english', %s)", sql)
        self.assertIn("ts_rank(to_tsvector('english', m.str), plainto_tsquery('english', %s), 1)", sql)
        self.assertIn("CASE WHEN lower(m.str) = lower(%s) THEN 1000.0", sql)
        # score param (SELECT) precedes WHERE params; limit last
        self.assertEqual(params, ["gene locus", "gene locus", "ENG", "gene locus", 50])

    def test_normalized_words(self):
        sql, params = L.build_search_sql("gene locus", "normalizedWords", lang=None)
        self.assertIn("to_tsvector('simple', m.str) @@ plainto_tsquery('simple', %s)", sql)
        self.assertNotIn("m.lat", sql)
        self.assertEqual(params, ["gene locus", "gene locus", "gene locus", 200])

    def test_normalized_string(self):
        sql, params = L.build_search_sql("Genome-wide, association  study", "normalizedString")
        self.assertIn("plainto_tsquery('simple', %s)", sql)
        self.assertIn("regexp_replace(lower(m.str), '[^[:alnum:]]+', ' ', 'g') = %s", sql)
        self.assertEqual(params, ["ENG", "Genome-wide, association  study",
                                  "genome wide association study", 200])

    def test_partial(self):
        sql, params = L.build_search_sql("genome wide association", "words", partial=True)
        self.assertIn("websearch_to_tsquery('english', %s)", sql)
        self.assertIn("OR lower(m.str) %% lower(%s)", sql)   # psycopg-escaped trigram op
        self.assertIn("similarity(lower(m.str), lower(%s))", sql)
        self.assertEqual(params, ["genome wide association", "ENG",
                                  "genome or wide or association",
                                  "genome wide association", 200])
        self.assertIn("ORDER BY score DESC", sql)

    def test_sabs_and_semantic_types(self):
        sql, params = L.build_search_sql("locus", "exact", sabs="MSH, NCI",
                                         semantic_types="T082,T028")
        self.assertIn("m.sab = ANY(%s)", sql)
        self.assertIn("EXISTS (SELECT 1 FROM mrsty t WHERE t.cui = m.cui AND t.tui = ANY(%s))", sql)
        self.assertEqual(params, ["ENG", "locus", ["MSH", "NCI"], ["T082", "T028"], 200])
        # list inputs work too
        _, p2 = L.build_search_sql("locus", "exact", sabs=["MSH"], semantic_types=["T082"])
        self.assertEqual(p2[2:4], [["MSH"], ["T082"]])

    def test_page_size_cap_and_floor(self):
        self.assertEqual(L.build_search_sql("x", "exact", page_size=99999)[1][-1], L.MAX_PAGE_SIZE)
        self.assertEqual(L.build_search_sql("x", "exact", page_size=0)[1][-1], 200)
        self.assertEqual(L.build_search_sql("x", "exact", page_size=-5)[1][-1], 1)

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            L.build_search_sql("x", "leftTruncation")

    def test_other_builders(self):
        sql, params = L.build_concepts_by_tui_sql("T082,T028", limit=10)
        self.assertIn("s.tui = ANY(%s)", sql)
        self.assertEqual(params, [["T082", "T028"], 10])
        sql, params = L.build_concepts_by_tui_sql(["T082"])
        self.assertNotIn("LIMIT %s", sql)     # only the LATERAL's LIMIT 1 remains
        sql, params = L.build_strings_like_sql("genom wide", limit=20)
        self.assertIn("lower(str) %% lower(%s)", sql)
        self.assertIn("similarity(lower(str), lower(%s)) AS similarity", sql)
        self.assertEqual(params, ["genom wide", "genom wide", "ENG", 20])
        sql, params = L.build_set_similarity_sql(0.4)
        self.assertIn("set_config('pg_trgm.similarity_threshold', %s, true)", sql)
        self.assertEqual(params, ["0.4"])
        sql, params = L.build_atoms_sql("C9000001", 5)
        self.assertIn("WHERE c.cui = %s", sql)
        self.assertEqual(params, ["C9000001", 5])
        sql, _ = L.build_concept_sql("C9000001")
        self.assertIn("AS atom_count", sql)
        self.assertIn("AS tuis", sql)
        sql, _ = L.build_sources_sql()
        self.assertIn("GROUP BY sab", sql)
        sql, _ = L.build_release_sql()
        self.assertIn("FROM umls_release ORDER BY loaded_at DESC LIMIT 1", sql)
        self.assertIn("DELETE FROM mrsty", L.build_prune_sty_sql())

    def test_normalize_string(self):
        self.assertEqual(L.normalize_string("  Genome-wide, (Association)  STUDY "),
                         "genome wide association study")


class TestDryRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = _write_fixture(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _main(self, *extra):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = L.main(["--rrf-dir", str(self.dir), "--release", "2026AA", "--dry-run", *extra])
        return rc, buf.getvalue()

    def test_counts_default_english(self):
        rc, out = self._main()
        self.assertEqual(rc, 0)
        self.assertIn("MRCONSO: read 6, kept 4 (dropped: language 2, sab 0; malformed skipped 1)", out)
        self.assertIn("MRSTY:   read 3, kept 3 (malformed skipped 0)", out)
        self.assertIn("CREATE TABLE IF NOT EXISTS mrconso", out)
        self.assertIn("COPY mrconso (", out)
        self.assertIn("CREATE EXTENSION IF NOT EXISTS pg_trgm;", out)
        self.assertIn("INSERT INTO umls_release", out)

    def test_counts_all_languages_and_sabs(self):
        _, out = self._main("--lang", "ALL", "--sabs", "MSH,NCI")
        self.assertIn("MRCONSO: read 6, kept 3 (dropped: language 0, sab 3;", out)

    def test_skip_indexes_omits_index_sql(self):
        _, out = self._main("--skip-indexes")
        self.assertNotIn("gin_trgm_ops", out)

    def test_dry_run_returns_stats(self):
        stats = L.dry_run(self.dir, "ENG", {"MSH"}, out=io.StringIO())
        self.assertEqual(stats["mrconso"]["kept"], 1)
        self.assertEqual(stats["mrconso"]["dropped_sab"], 3)
        self.assertEqual(stats["mrsty"]["kept"], 3)


# --------------------------------------------------------------------------
# Fakes for the DB-touching paths
# --------------------------------------------------------------------------

class FakeCopy:
    def __init__(self, sql, sink):
        self.sql = sql
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def write_row(self, row):
        self.sink.append((self.sql, list(row)))


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self._rows = []
        self.rowcount = -1

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.conn.executed.append((sql, params))
        self.rowcount = -1
        self.description = None
        self._rows = []
        if sql.startswith("SELECT count(*) FROM mrconso"):
            self._rows = [(self.conn.existing_rows,)]
        elif sql.startswith("DELETE FROM mrsty"):
            self.rowcount = self.conn.pruned
        else:
            for pred, (cols, rows) in self.conn.canned:
                if pred(sql):
                    self.description = [(c,) for c in cols]
                    self._rows = rows
                    break

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def copy(self, sql):
        return FakeCopy(sql, self.conn.copied)


class FakeConn:
    def __init__(self, existing_rows=0, pruned=0, canned=None):
        self.executed = []
        self.copied = []
        self.existing_rows = existing_rows
        self.pruned = pruned
        self.canned = canned or []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


class TestLoaderWithFakePsycopg(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = _write_fixture(Path(self.tmp.name))
        self.conn = FakeConn(pruned=1)
        fake = types.ModuleType("psycopg")
        connections = []

        def connect(dsn, autocommit=False):
            connections.append((dsn, autocommit))
            return self.conn
        fake.connect = connect
        self.connections = connections
        self._saved = sys.modules.get("psycopg")
        sys.modules["psycopg"] = fake

    def tearDown(self):
        if self._saved is None:
            sys.modules.pop("psycopg", None)
        else:
            sys.modules["psycopg"] = self._saved
        self.tmp.cleanup()

    def test_loader_copies_rows_and_records_release(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = L.main(["--rrf-dir", str(self.dir), "--release", "2026AA",
                         "--dsn", "postgresql:///umls_test", "--batch", "2"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.connections, [("postgresql:///umls_test", True)])
        self.assertTrue(self.conn.closed)

        conso = [r for s, r in self.conn.copied if s.startswith("COPY mrconso")]
        sty = [r for s, r in self.conn.copied if s.startswith("COPY mrsty")]
        self.assertEqual(len(conso), 4)                 # ENG rows only, malformed skipped
        self.assertEqual(len(sty), 3)
        self.assertEqual(conso[0][0], "C9000001")
        self.assertEqual(conso[0][14], "Gene Locus")
        self.assertIsNone(conso[0][8])                  # empty SAUI -> NULL
        self.assertEqual(conso[0][17], "256")
        self.assertTrue(all(len(r) == 18 for r in conso))

        sqls = [s for s, _ in self.conn.executed]
        self.assertTrue(any(s.startswith("CREATE TABLE IF NOT EXISTS mrconso") for s in sqls))
        self.assertIn("CREATE EXTENSION IF NOT EXISTS pg_trgm", sqls)
        self.assertTrue(any("gin_trgm_ops" in s for s in sqls))
        self.assertTrue(any(s.startswith("DROP INDEX IF EXISTS mrconso_cui_idx") for s in sqls))
        self.assertIn(L.build_prune_sty_sql(), sqls)
        ins = [(s, p) for s, p in self.conn.executed if s.startswith("INSERT INTO umls_release")]
        self.assertEqual(len(ins), 1)
        self.assertEqual(ins[0][1], ["2026AA", str(self.dir), 4, 2, "ENG", None])
        self.assertIn("loaded 2026AA: mrconso 4 rows", buf.getvalue())

    def test_refuses_to_clobber_without_replace(self):
        self.conn.existing_rows = 7
        with self.assertRaises(SystemExit):
            L.load(self.dir, "postgresql:///x", "2026AA", "ENG", None, out=io.StringIO())
        self.assertFalse(self.conn.copied)
        # with --replace: truncates then loads
        L.load(self.dir, "postgresql:///x", "2026AA", "ENG", None, replace=True,
               skip_indexes=True, out=io.StringIO())
        sqls = [s for s, _ in self.conn.executed]
        self.assertIn("TRUNCATE mrconso, mrsty", sqls)
        self.assertFalse(any("gin_trgm_ops" in s for s in sqls))
        self.assertEqual(len(self.conn.copied), 7)

    def test_sabs_filter_applies_while_streaming(self):
        L.load(self.dir, None, "2026AA", None, {"NCI"}, skip_indexes=True, out=io.StringIO())
        conso = [r for s, r in self.conn.copied if s.startswith("COPY mrconso")]
        self.assertEqual({r[11] for r in conso}, {"NCI"})
        self.assertEqual(len(conso), 2)
        self.assertEqual(self.connections[0][0], L.DEFAULT_DSN)


class TestMissingPsycopg(unittest.TestCase):
    def test_clear_error(self):
        saved = sys.modules.get("psycopg")
        sys.modules["psycopg"] = None   # makes `import psycopg` raise ImportError
        try:
            with self.assertRaises(RuntimeError) as cm:
                L.PgUMLSClient(dsn="postgresql:///nope").search("x")
            self.assertIn("psycopg", str(cm.exception))
        finally:
            if saved is None:
                sys.modules.pop("psycopg", None)
            else:
                sys.modules["psycopg"] = saved


class TestPgUMLSClient(unittest.TestCase):
    """The client's result shaping over a fake connection with canned rows."""

    def _client(self, canned):
        conn = FakeConn(canned=canned)
        return L.PgUMLSClient(conn=conn), conn

    def test_search_shape_and_pre_statement(self):
        cols = ["cui", "name", "root_source", "score", "semantic_types"]
        rows = [("C9000001", "Gene Locus", "MSH", 0.9, ["Spatial Concept"]),
                ("C9000009", None, None, 0.1, None)]       # nameless row dropped
        client, conn = self._client([(lambda s: s.startswith("WITH hits"), (cols, rows))])
        res = client.search("gene locus", partial=True, semantic_types="T082")
        self.assertEqual(res, [{"cui": "C9000001", "name": "Gene Locus",
                                "root_source": "MSH", "semantic_types": ["Spatial Concept"]}])
        sqls = [s for s, _ in conn.executed]
        self.assertIn("set_config('pg_trgm.similarity_threshold'", sqls[0])
        self.assertIn("t.tui = ANY(%s)", sqls[1])
        # non-partial searches do not set the threshold
        conn.executed.clear()
        client.search("gene locus", search_type="exact")
        self.assertEqual(len(conn.executed), 1)
        self.assertEqual(client.search("   "), [])

    def test_search_signature_matches_uts(self):
        import inspect
        from forome.gem.umls.uts_client import UTSClient
        self.assertEqual(list(inspect.signature(L.PgUMLSClient.search).parameters),
                         list(inspect.signature(UTSClient.search).parameters))
        for m in ("sources", "get_concept", "atoms", "relations", "definitions",
                  "source_ancestors", "rollup", "get_semantic_type"):
            self.assertTrue(callable(getattr(L.PgUMLSClient, m)), m)

    def test_concept_atoms_sources_release(self):
        canned = [
            (lambda s: "AS atom_count" in s,
             (["cui", "name", "root_source", "semantic_types", "tuis", "atom_count"],
              [("C9000001", "Gene Locus", "MSH", ["Spatial Concept"], ["T082"], 3)])),
            (lambda s: s.startswith("SELECT c.sab, c.tty"),
             (["sab", "tty", "name", "language", "code", "suppress"],
              [("MSH", "MH", "Gene Locus", "ENG", "D000001", "N"),
               ("NCI", "SY", "GWAS", "ENG", "C12345", "O"),
               ("NCI", "SY", "gwas", "ENG", "C12345", "Y")])),
            (lambda s: "GROUP BY sab" in s,
             (["sab", "language", "n"], [("MSH", "ENG", 2), ("NCI", "ENG", 2)])),
            (lambda s: s.startswith("SELECT version"),
             (["version", "loaded_at", "source_dir", "rows_mrconso", "rows_mrsty", "lang", "sabs"],
              [("2026AA", "2026-08-30", "/x/META", 4, 3, "ENG", None)])),
            (lambda s: "s.tui = ANY(%s)" in s and "DISTINCT" in s,
             (["cui", "name", "semantic_types"], [("C9000001", "Gene Locus", ["Spatial Concept"])])),
            (lambda s: "AS similarity" in s,
             (["cui", "str", "sab", "tty", "similarity"],
              [("C9000002", "GWAS", "NCI", "SY", 0.55)])),
        ]
        client, conn = self._client(canned)
        c = client.get_concept("C9000001")
        self.assertEqual(c["name"], "Gene Locus")
        self.assertEqual(c["semantic_type_details"], [{"name": "Spatial Concept", "tui": "T082"}])
        self.assertEqual(c["atom_count"], 3)
        atoms = client.atoms("C9000001")
        self.assertEqual([a["obsolete"] for a in atoms], [False, True, False])
        self.assertEqual([a["suppressible"] for a in atoms], [False, True, True])
        self.assertEqual(atoms[0]["code"], "D000001")
        self.assertEqual(set(atoms[0]), {"sab", "tty", "name", "language", "code",
                                         "obsolete", "suppressible"})
        src = client.sources()
        self.assertEqual(src[0], {"sab": "MSH", "name": "MSH", "language": "ENG", "count": 2})
        self.assertEqual(client.release()["version"], "2026AA")
        self.assertEqual(client.concepts_by_tui("T082")[0]["cui"], "C9000001")
        self.assertEqual(client.concepts_by_tui("")[0:0], [])
        like = client.strings_like("gwas", min_similarity=0.5)
        self.assertEqual(like, [{"cui": "C9000002", "str": "GWAS", "sab": "NCI",
                                 "tty": "SY", "similarity": 0.55}])
        self.assertEqual(client.relations("C9000001"), [])
        self.assertEqual(client.definitions("C9000001"), [])
        self.assertEqual(client.rollup("C9000001"), [])
        # unknown concept -> None
        client2, _ = self._client([(lambda s: "AS atom_count" in s,
                                    (["cui", "name"], [("C0", None)]))])
        self.assertIsNone(client2.get_concept("C0"))


if __name__ == "__main__":
    unittest.main()
