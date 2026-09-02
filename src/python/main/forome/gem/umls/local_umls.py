#!/usr/bin/env python3
"""Local UMLS Metathesaurus index on PostgreSQL, behind the UTS client interface.

Two things live here:

* **A loader** (``gem-umls-load-local`` / ``main``) that streams the RRF files of
  a UMLS release (``MRCONSO.RRF``, ``MRSTY.RRF``) into two PostgreSQL tables via
  ``COPY``, builds the search indexes (btree, full-text GIN, trigram GIN) and
  records the release in ``umls_release``. Designed for ~9M English rows: the
  files are never read into memory.

* **``PgUMLSClient``** -- a drop-in for ``uts_client.UTSClient`` for the
  operations that only need atoms + semantic types (``search``, ``get_concept``,
  ``atoms``, ``sources``) plus local-only extras (``concepts_by_tui``,
  ``strings_like``, ``release``). Relations, definitions and hierarchy rollups
  are *not* indexed locally and stay on UTS (they return ``[]`` here).

All SQL is produced by small pure functions (``build_schema_sql``,
``build_index_sql``, ``build_search_sql`` ...) returning ``(sql, params)`` so
the query logic is unit-testable without a database. ``psycopg`` (v3) is
imported lazily, only on the code paths that actually touch PostgreSQL.

The RRF files are licensed content: keep them **outside** the repository and
never commit them or a database dump (see data/umls/README.md).
"""
from __future__ import annotations

import argparse
import gzip
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Iterable, Iterator, Optional

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# RRF layout
# --------------------------------------------------------------------------

MRCONSO_COLUMNS = ["CUI", "LAT", "TS", "LUI", "STT", "SUI", "ISPREF", "AUI",
                   "SAUI", "SCUI", "SDUI", "SAB", "TTY", "CODE", "STR", "SRL",
                   "SUPPRESS", "CVF"]
MRSTY_COLUMNS = ["CUI", "TUI", "STN", "STY", "ATUI", "CVF"]

DEFAULT_DSN = "postgresql:///umls"
DSN_ENV = "GEM_UMLS_DSN"
MAX_PAGE_SIZE = 1000
DEFAULT_MIN_SIMILARITY = 0.3
COPY_BATCH = 50_000

# The distinct search types the harness / UI use, mapped onto SQL below.
SEARCH_TYPES = ("exact", "words", "normalizedWords", "normalizedString")


def iter_rrf(path: str | os.PathLike, ncols: int,
             stats: Optional[dict] = None,
             max_warnings: int = 10) -> Iterator[list[str]]:
    """Stream the rows of an RRF file as lists of ``ncols`` strings.

    RRF is pipe-delimited with **no quoting** and a **trailing pipe** on every
    line, UTF-8 encoded. Lines with the wrong number of fields (short or long)
    are skipped with a warning; ``stats`` (if given) is updated in place with
    ``rows`` (yielded) and ``skipped`` counts, so the caller of a generator can
    still report them. ``.gz`` files are read transparently.
    """
    path = Path(path)
    if stats is None:
        stats = {}
    stats.setdefault("rows", 0)
    stats.setdefault("skipped", 0)
    opener = gzip.open if path.suffix == ".gz" else open
    warned = 0
    with opener(path, "rt", encoding="utf-8", newline="\n") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("|")
            # A well-formed line splits into ncols fields plus an empty tail.
            if len(parts) == ncols + 1 and parts[-1] == "":
                stats["rows"] += 1
                yield parts[:-1]
                continue
            stats["skipped"] += 1
            if warned < max_warnings:
                warned += 1
                log.warning("%s:%d: expected %d fields, got %d -- skipped",
                            path.name, lineno, ncols,
                            len(parts) - (1 if parts and parts[-1] == "" else 0))
    if stats["skipped"] > max_warnings:
        log.warning("%s: %d malformed lines skipped in total",
                    path.name, stats["skipped"])


# --------------------------------------------------------------------------
# SQL: schema and indexes (pure functions)
# --------------------------------------------------------------------------

MRCONSO_TABLE = "mrconso"
MRSTY_TABLE = "mrsty"
RELEASE_TABLE = "umls_release"

# Index names are fixed so a reload can drop and rebuild them.
INDEXES: list[tuple[str, str]] = [
    ("mrconso_cui_idx", f"CREATE INDEX IF NOT EXISTS mrconso_cui_idx ON {MRCONSO_TABLE} USING btree (cui)"),
    ("mrconso_sab_idx", f"CREATE INDEX IF NOT EXISTS mrconso_sab_idx ON {MRCONSO_TABLE} USING btree (sab)"),
    # Equality on lower(str). A *hash* index rather than btree on purpose: a few
    # Metathesaurus strings exceed the btree row-size cap (~2.7 kB), which would
    # abort the build; hash has no such limit and serves `lower(str) = ...`.
    ("mrconso_lower_str_idx", f"CREATE INDEX IF NOT EXISTS mrconso_lower_str_idx ON {MRCONSO_TABLE} USING hash (lower(str))"),
    ("mrconso_str_english_idx", f"CREATE INDEX IF NOT EXISTS mrconso_str_english_idx ON {MRCONSO_TABLE} USING gin (to_tsvector('english', str))"),
    ("mrconso_str_simple_idx", f"CREATE INDEX IF NOT EXISTS mrconso_str_simple_idx ON {MRCONSO_TABLE} USING gin (to_tsvector('simple', str))"),
    ("mrconso_str_trgm_idx", f"CREATE INDEX IF NOT EXISTS mrconso_str_trgm_idx ON {MRCONSO_TABLE} USING gin (lower(str) gin_trgm_ops)"),
    ("mrsty_cui_idx", f"CREATE INDEX IF NOT EXISTS mrsty_cui_idx ON {MRSTY_TABLE} USING btree (cui)"),
    ("mrsty_tui_idx", f"CREATE INDEX IF NOT EXISTS mrsty_tui_idx ON {MRSTY_TABLE} USING btree (tui)"),
]


def build_schema_sql() -> list[str]:
    """DDL for the three tables (idempotent: ``CREATE TABLE IF NOT EXISTS``)."""
    conso_cols = ",\n".join(f"    {c.lower()} text" for c in MRCONSO_COLUMNS)
    sty_cols = ",\n".join(f"    {c.lower()} text" for c in MRSTY_COLUMNS)
    return [
        f"CREATE TABLE IF NOT EXISTS {MRCONSO_TABLE} (\n{conso_cols}\n)",
        f"CREATE TABLE IF NOT EXISTS {MRSTY_TABLE} (\n{sty_cols}\n)",
        f"CREATE TABLE IF NOT EXISTS {RELEASE_TABLE} (\n"
        "    version text NOT NULL,\n"
        "    loaded_at timestamptz NOT NULL DEFAULT now(),\n"
        "    source_dir text,\n"
        "    rows_mrconso bigint,\n"
        "    rows_mrsty bigint,\n"
        "    lang text,\n"
        "    sabs text\n"
        ")",
    ]


def build_index_sql() -> list[str]:
    """Index DDL, preceded by the ``pg_trgm`` extension the trigram index needs."""
    return ["CREATE EXTENSION IF NOT EXISTS pg_trgm"] + [ddl for _, ddl in INDEXES]


def build_drop_index_sql() -> list[str]:
    """Drop the indexes before a bulk reload (COPY is much faster without them)."""
    return [f"DROP INDEX IF EXISTS {name}" for name, _ in INDEXES]


def build_copy_sql(table: str, columns: list[str]) -> str:
    cols = ", ".join(c.lower() for c in columns)
    return f"COPY {table} ({cols}) FROM STDIN"


def build_release_insert_sql() -> str:
    return (f"INSERT INTO {RELEASE_TABLE} "
            "(version, source_dir, rows_mrconso, rows_mrsty, lang, sabs) "
            "VALUES (%s, %s, %s, %s, %s, %s)")


def build_prune_sty_sql() -> str:
    """Drop semantic-type rows for CUIs that have no loaded atom (e.g. no
    English string, or outside the ``--sabs`` subset)."""
    return (f"DELETE FROM {MRSTY_TABLE} s WHERE NOT EXISTS "
            f"(SELECT 1 FROM {MRCONSO_TABLE} m WHERE m.cui = s.cui)")


# --------------------------------------------------------------------------
# SQL: queries (pure functions returning (sql, params))
# --------------------------------------------------------------------------

def _split_list(value) -> Optional[list[str]]:
    """A comma-joined string (the UTS convention), a list, or None -> list|None."""
    if value is None:
        return None
    if isinstance(value, str):
        items = [x.strip() for x in value.split(",")]
    else:
        items = [str(x).strip() for x in value]
    items = [x for x in items if x]
    return items or None


def normalize_string(term: str) -> str:
    """The client-side twin of the SQL ``normalizedString`` expression:
    lower-case, every run of non-alphanumerics collapsed to one space."""
    out, prev_space = [], True
    for ch in term.lower():
        if ch.isalnum():
            out.append(ch)
            prev_space = False
        elif not prev_space:
            out.append(" ")
            prev_space = True
    return "".join(out).strip()


# Preferred name of a CUI: the MTH-preferred English atom when available.
# Ordering is by the same flags UTS uses for the concept name (TS=P preferred
# LUI, STT=PF preferred form, ISPREF=Y preferred AUI), with non-suppressed
# atoms first and a deterministic tie-break.
_PREFERRED_ATOM_ORDER = (
    "(c.lat = 'ENG') DESC, (c.ts = 'P') DESC, (c.stt = 'PF') DESC, "
    "(c.ispref = 'Y') DESC, (c.suppress = 'N') DESC, c.sab, c.aui")

_PREFERRED_JOIN = (
    "LEFT JOIN LATERAL (\n"
    f"  SELECT c.str, c.sab FROM {MRCONSO_TABLE} c WHERE c.cui = h.cui\n"
    f"  ORDER BY {_PREFERRED_ATOM_ORDER} LIMIT 1\n"
    ") p ON true")

_STY_SUBSELECT = (
    "(SELECT coalesce(array_agg(s.sty ORDER BY s.sty), ARRAY[]::text[])\n"
    f"   FROM {MRSTY_TABLE} s WHERE s.cui = h.cui) AS semantic_types")


def build_set_similarity_sql(min_similarity: float = DEFAULT_MIN_SIMILARITY) -> tuple[str, list]:
    """Transaction-local trigram threshold used by the ``%`` operator (so the
    trigram GIN index is used, unlike ``similarity(...) > x``)."""
    return ("SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
            [str(float(min_similarity))])


def build_search_sql(term: str, search_type: str = "words",
                     sabs=None, page_size: int = 200,
                     semantic_types=None, partial: bool = False,
                     lang: Optional[str] = "ENG") -> tuple[str, list]:
    """SQL + params for ``PgUMLSClient.search``.

    Match clause by ``search_type`` (``partial`` overrides it):

    * ``exact``            ``lower(str) = lower(term)``
    * ``words``            ``to_tsvector('english', str) @@ plainto_tsquery('english', term)``
    * ``normalizedWords``  same with the ``simple`` configuration (no stemming)
    * ``normalizedString`` the ``simple`` tsquery (index) **and** the whole
                           punctuation-folded string equal to the folded term
    * ``partial``          ``websearch_to_tsquery('english', w1 or w2 ...)`` --
                           any word may match -- OR trigram-similar
                           (``lower(str) % lower(term)``), ranked by similarity

    ``sabs`` / ``semantic_types`` are comma-joined lists (UTS convention) or
    sequences and become ``= ANY(%s)`` filters; ``semantic_types`` are TUIs
    resolved through ``mrsty``. Results are one row per CUI with the preferred
    name, its SAB and the semantic-type names, capped at ``page_size``.
    """
    if partial:
        mode = "partial"
    elif search_type in SEARCH_TYPES:
        mode = search_type
    else:
        raise ValueError(f"unsupported search_type {search_type!r}; "
                         f"expected one of {SEARCH_TYPES} or partial=True")

    where: list[str] = []
    params: list = []
    if lang:
        where.append("m.lat = %s")
        params.append(lang)

    if mode == "exact":
        where.append("lower(m.str) = lower(%s)")
        params.append(term)
        score = "1.0"
    elif mode == "words":
        where.append("to_tsvector('english', m.str) @@ plainto_tsquery('english', %s)")
        params.append(term)
        # exact-name bonus + length-normalized rank (flag 1: /(1+log(len))) --
        # otherwise long clinical strings repeating the term outrank the
        # concept actually named by it.
        score = ("(CASE WHEN lower(m.str) = lower(%s) THEN 1000.0 ELSE 0.0 END)"
                 " + ts_rank(to_tsvector('english', m.str),"
                 " plainto_tsquery('english', %s), 1)")
    elif mode == "normalizedWords":
        where.append("to_tsvector('simple', m.str) @@ plainto_tsquery('simple', %s)")
        params.append(term)
        score = ("(CASE WHEN lower(m.str) = lower(%s) THEN 1000.0 ELSE 0.0 END)"
                 " + ts_rank(to_tsvector('simple', m.str),"
                 " plainto_tsquery('simple', %s), 1)")
    elif mode == "normalizedString":
        where.append("to_tsvector('simple', m.str) @@ plainto_tsquery('simple', %s)")
        params.append(term)
        where.append("regexp_replace(lower(m.str), '[^[:alnum:]]+', ' ', 'g') = %s")
        params.append(normalize_string(term))
        score = "1.0"
    else:  # partial
        any_word = " or ".join(term.split()) or term
        where.append("(to_tsvector('english', m.str) @@ websearch_to_tsquery('english', %s)"
                     " OR lower(m.str) %% lower(%s))")
        params.extend([any_word, term])
        score = "similarity(lower(m.str), lower(%s))"

    score_params: list = [term] * score.count("%s")

    sab_list = _split_list(sabs)
    if sab_list:
        where.append("m.sab = ANY(%s)")
        params.append(sab_list)
    tui_list = _split_list(semantic_types)
    if tui_list:
        where.append(f"EXISTS (SELECT 1 FROM {MRSTY_TABLE} t WHERE t.cui = m.cui AND t.tui = ANY(%s))")
        params.append(tui_list)

    limit = max(1, min(int(page_size or 200), MAX_PAGE_SIZE))
    sql = (
        "WITH hits AS (\n"
        f"  SELECT m.cui, max({score}) AS score\n"
        f"  FROM {MRCONSO_TABLE} m\n"
        f"  WHERE {' AND '.join(where)}\n"
        "  GROUP BY m.cui\n"
        "  ORDER BY score DESC, m.cui\n"
        "  LIMIT %s\n"
        ")\n"
        "SELECT h.cui, p.str AS name, p.sab AS root_source, h.score,\n"
        f"       {_STY_SUBSELECT}\n"
        "FROM hits h\n"
        f"{_PREFERRED_JOIN}\n"
        "ORDER BY h.score DESC, h.cui"
    )
    return sql, score_params + params + [limit]


def build_concepts_by_tui_sql(tuis, limit: Optional[int] = None) -> tuple[str, list]:
    tui_list = _split_list(tuis) or []
    sql = (
        "WITH hits AS (\n"
        f"  SELECT DISTINCT s.cui FROM {MRSTY_TABLE} s WHERE s.tui = ANY(%s)\n"
        "  ORDER BY s.cui" + ("\n  LIMIT %s" if limit else "") + "\n"
        ")\n"
        "SELECT h.cui, p.str AS name, p.sab AS root_source,\n"
        f"       {_STY_SUBSELECT}\n"
        "FROM hits h\n"
        f"{_PREFERRED_JOIN}\n"
        "ORDER BY h.cui"
    )
    params: list = [tui_list]
    if limit:
        params.append(int(limit))
    return sql, params


def build_sty_backfill_sql(types: list[dict]) -> tuple[str, list]:
    """Fill MRSTY's ``sty``/``stn`` from the Semantic Network reference where the
    release left them blank (the raw full-release MRSTY.RRF carries only
    CUI|TUI). ``types`` = [{tui, name, tree_number}] (semantic_types.py)."""
    rows = [(t["tui"], t["name"], t.get("tree_number") or "") for t in types if t.get("tui")]
    if not rows:
        return ("SELECT 0", [])
    values = ", ".join(["(%s, %s, %s)"] * len(rows))
    sql = (f"UPDATE {MRSTY_TABLE} AS s SET sty = v.name, stn = v.stn\n"
           f"FROM (VALUES {values}) AS v(tui, name, stn)\n"
           "WHERE s.tui = v.tui AND (s.sty IS NULL OR s.sty = '')")
    params: list = [x for r in rows for x in r]
    return sql, params


def build_strings_like_sql(term: str, limit: int = 200,
                           lang: Optional[str] = "ENG") -> tuple[str, list]:
    """Trigram-similar strings (the threshold comes from
    ``build_set_similarity_sql``, executed first in the same transaction)."""
    where = ["lower(str) %% lower(%s)"]
    params: list = [term]
    if lang:
        where.append("lat = %s")
        params.append(lang)
    sql = (
        "SELECT cui, str, sab, tty, similarity(lower(str), lower(%s)) AS similarity\n"
        f"FROM {MRCONSO_TABLE}\n"
        f"WHERE {' AND '.join(where)}\n"
        "ORDER BY similarity DESC, cui, aui\n"
        "LIMIT %s"
    )
    return sql, [term] + params + [max(1, int(limit))]


def build_sources_sql() -> tuple[str, list]:
    return (
        "SELECT sab, mode() WITHIN GROUP (ORDER BY lat) AS language, count(*) AS n\n"
        f"FROM {MRCONSO_TABLE} GROUP BY sab ORDER BY sab", [])


def build_concept_sql(cui: str) -> tuple[str, list]:
    sql = (
        "WITH hits AS (SELECT %s::text AS cui)\n"
        "SELECT h.cui, p.str AS name, p.sab AS root_source,\n"
        f"       {_STY_SUBSELECT},\n"
        f"       (SELECT coalesce(array_agg(s.tui ORDER BY s.sty), ARRAY[]::text[])\n"
        f"          FROM {MRSTY_TABLE} s WHERE s.cui = h.cui) AS tuis,\n"
        f"       (SELECT count(*) FROM {MRCONSO_TABLE} a WHERE a.cui = h.cui) AS atom_count\n"
        "FROM hits h\n"
        f"{_PREFERRED_JOIN}"
    )
    return sql, [cui]


def build_atoms_sql(cui: str, limit: int = 300) -> tuple[str, list]:
    sql = (
        "SELECT c.sab, c.tty, c.str AS name, c.lat AS language, c.code, c.suppress\n"
        f"FROM {MRCONSO_TABLE} c WHERE c.cui = %s\n"
        f"ORDER BY {_PREFERRED_ATOM_ORDER}\n"
        "LIMIT %s"
    )
    return sql, [cui, max(1, int(limit))]


def build_release_sql() -> tuple[str, list]:
    return (
        "SELECT version, loaded_at, source_dir, rows_mrconso, rows_mrsty, lang, sabs\n"
        f"FROM {RELEASE_TABLE} ORDER BY loaded_at DESC LIMIT 1", [])


# --------------------------------------------------------------------------
# psycopg (lazy)
# --------------------------------------------------------------------------

def _psycopg():
    """Import psycopg 3 on demand with an actionable error if it is missing."""
    try:
        import psycopg  # type: ignore
    except ImportError as e:  # pragma: no cover - exercised only without psycopg
        raise RuntimeError(
            "The local UMLS index needs psycopg 3 (PostgreSQL driver). Install it "
            "with:  pip install 'psycopg[binary]'   or   pip install -e '.[local]'"
        ) from e
    return psycopg


def _connect(dsn: Optional[str]):
    dsn = dsn or os.environ.get(DSN_ENV) or DEFAULT_DSN
    return _psycopg().connect(dsn, autocommit=True)


def _rows_as_dicts(cur) -> list[dict]:
    """Fetch every row of the executed cursor as a dict (driver-agnostic)."""
    desc = cur.description or []
    cols = [getattr(d, "name", None) or d[0] for d in desc]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# --------------------------------------------------------------------------
# Loader
# --------------------------------------------------------------------------

def _rrf_path(rrf_dir: Path, name: str) -> Path:
    for cand in (rrf_dir / name, rrf_dir / f"{name}.gz"):
        if cand.is_file():
            return cand
    raise FileNotFoundError(f"{name} not found in {rrf_dir}")


def filtered_mrconso(rrf_dir: Path, lang: Optional[str], sabs: Optional[set],
                     stats: dict) -> Iterator[list[str]]:
    """Stream MRCONSO rows, applying the LAT and SAB filters; ``stats`` gets
    ``read``, ``kept``, ``dropped_lang``, ``dropped_sab``, ``skipped``."""
    parse = {}
    stats.update({"read": 0, "kept": 0, "dropped_lang": 0, "dropped_sab": 0})
    i_lat, i_sab = MRCONSO_COLUMNS.index("LAT"), MRCONSO_COLUMNS.index("SAB")
    for row in iter_rrf(_rrf_path(rrf_dir, "MRCONSO.RRF"), len(MRCONSO_COLUMNS), parse):
        stats["read"] += 1
        if lang and row[i_lat] != lang:
            stats["dropped_lang"] += 1
            continue
        if sabs and row[i_sab] not in sabs:
            stats["dropped_sab"] += 1
            continue
        stats["kept"] += 1
        yield row
    stats["skipped"] = parse.get("skipped", 0)


def filtered_mrsty(rrf_dir: Path, stats: dict) -> Iterator[list[str]]:
    parse = {}
    stats.update({"read": 0, "kept": 0})
    for row in iter_rrf(_rrf_path(rrf_dir, "MRSTY.RRF"), len(MRSTY_COLUMNS), parse):
        stats["read"] += 1
        stats["kept"] += 1
        yield row
    stats["skipped"] = parse.get("skipped", 0)


def _copy_rows(cur, table: str, columns: list[str], rows: Iterable[list[str]],
               batch: int = COPY_BATCH, progress: Optional[Callable[[int], None]] = None) -> int:
    """Stream ``rows`` into ``table`` with COPY, one COPY statement per
    ``batch`` rows (bounded memory, periodic progress). Empty fields -> NULL."""
    sql = build_copy_sql(table, columns)
    total = 0
    chunk: list = []

    def flush():
        nonlocal total
        if not chunk:
            return
        with cur.copy(sql) as copy:
            for r in chunk:
                copy.write_row([v if v != "" else None for v in r])
        total += len(chunk)
        chunk.clear()
        if progress:
            progress(total)

    for row in rows:
        chunk.append(row)
        if len(chunk) >= batch:
            flush()
    flush()
    return total


def dry_run(rrf_dir: Path, lang: Optional[str], sabs: Optional[set],
            skip_indexes: bool = False, out=None) -> dict:
    """Parse the files and report counts per filter plus the SQL; no database."""
    out = out or sys.stdout
    conso, sty = {}, {}
    for _ in filtered_mrconso(rrf_dir, lang, sabs, conso):
        pass
    for _ in filtered_mrsty(rrf_dir, sty):
        pass
    print(f"MRCONSO: read {conso['read']}, kept {conso['kept']} "
          f"(dropped: language {conso['dropped_lang']}, sab {conso['dropped_sab']}; "
          f"malformed skipped {conso['skipped']})", file=out)
    print(f"MRSTY:   read {sty['read']}, kept {sty['kept']} "
          f"(malformed skipped {sty['skipped']})", file=out)
    print("\n-- schema", file=out)
    for s in build_schema_sql():
        print(s + ";", file=out)
    print("\n-- copy", file=out)
    print(build_copy_sql(MRCONSO_TABLE, MRCONSO_COLUMNS) + ";", file=out)
    print(build_copy_sql(MRSTY_TABLE, MRSTY_COLUMNS) + ";", file=out)
    if not skip_indexes:
        print("\n-- indexes", file=out)
        for s in build_index_sql():
            print(s + ";", file=out)
    print("\n-- release", file=out)
    print(build_release_insert_sql() + ";", file=out)
    return {"mrconso": conso, "mrsty": sty}


def load(rrf_dir: Path, dsn: Optional[str], release: str,
         lang: Optional[str], sabs: Optional[set], skip_indexes: bool = False,
         replace: bool = False, batch: int = COPY_BATCH, out=None,
         conn=None) -> dict:
    """Load the release into PostgreSQL. ``conn`` may be injected (tests)."""
    out = out or sys.stdout
    own = conn is None
    if own:
        conn = _connect(dsn)
    try:
        with conn.cursor() as cur:
            for s in build_schema_sql():
                cur.execute(s)
            cur.execute(f"SELECT count(*) FROM {MRCONSO_TABLE}")
            existing = cur.fetchone()[0]
            if existing:
                if not replace:
                    raise SystemExit(
                        f"{MRCONSO_TABLE} already holds {existing} rows; "
                        "rerun with --replace to truncate and reload.")
                print(f"replacing {existing} existing rows", file=out)
                cur.execute(f"TRUNCATE {MRCONSO_TABLE}, {MRSTY_TABLE}")
            for s in build_drop_index_sql():
                cur.execute(s)

            conso, sty = {}, {}
            n_conso = _copy_rows(
                cur, MRCONSO_TABLE, MRCONSO_COLUMNS,
                filtered_mrconso(rrf_dir, lang, sabs, conso), batch,
                progress=lambda n: print(f"  mrconso: {n} rows", file=out))
            n_sty = _copy_rows(
                cur, MRSTY_TABLE, MRSTY_COLUMNS, filtered_mrsty(rrf_dir, sty), batch,
                progress=lambda n: print(f"  mrsty: {n} rows", file=out))
            if not skip_indexes:
                print("building indexes (this takes a while) ...", file=out)
                for s in build_index_sql():
                    print(f"  {s.split(' ON ')[0]}", file=out)
                    cur.execute(s)
            cur.execute(build_prune_sty_sql())
            pruned = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            # the raw full-release MRSTY.RRF carries only CUI|TUI (STN/STY blank):
            # name the types from the Semantic Network reference we ship
            from forome.gem.umls import semantic_types as stylib
            bsql, bparams = build_sty_backfill_sql(list(stylib._load().values()))
            cur.execute(bsql, bparams)
            named = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            if named:
                print(f"  mrsty: named {named} rows from the Semantic Network reference",
                      file=out)
            cur.execute(build_release_insert_sql(),
                        [release, str(rrf_dir), n_conso, n_sty - pruned, lang or "ALL",
                         ",".join(sorted(sabs)) if sabs else None])
            cur.execute("ANALYZE " + MRCONSO_TABLE)
            cur.execute("ANALYZE " + MRSTY_TABLE)
        print(f"loaded {release}: mrconso {n_conso} rows "
              f"(read {conso['read']}, dropped language {conso['dropped_lang']}, "
              f"sab {conso['dropped_sab']}, malformed {conso['skipped']}); "
              f"mrsty {n_sty - pruned} rows (pruned {pruned} without atoms)", file=out)
        return {"mrconso": conso, "mrsty": sty, "rows_mrconso": n_conso,
                "rows_mrsty": n_sty - pruned}
    finally:
        if own:
            conn.close()


def _parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="gem-umls-load-local",
        description="Load a UMLS release (MRCONSO.RRF + MRSTY.RRF) into a local "
                    "PostgreSQL index used by forome.gem.umls.local_umls.PgUMLSClient.")
    ap.add_argument("--rrf-dir", required=True,
                    help="directory holding MRCONSO.RRF and MRSTY.RRF (e.g. ~/umls/2026AA/META)")
    ap.add_argument("--dsn", default=None,
                    help=f"PostgreSQL DSN (default: ${DSN_ENV}, else {DEFAULT_DSN})")
    ap.add_argument("--release", required=True, help="release label, e.g. 2026AA")
    ap.add_argument("--lang", default="ENG",
                    help="LAT to keep (default ENG); ALL keeps every language")
    ap.add_argument("--sabs", default=None,
                    help="optional comma list of source vocabularies to keep")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse the files, print counts per filter and the SQL; no database")
    ap.add_argument("--skip-indexes", action="store_true",
                    help="load the tables only (indexes can be built later with build_index_sql)")
    ap.add_argument("--replace", action="store_true",
                    help="truncate an existing load before loading")
    ap.add_argument("--batch", type=int, default=COPY_BATCH,
                    help=f"rows per COPY statement (default {COPY_BATCH})")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    a = _parse_args(argv)
    rrf_dir = Path(a.rrf_dir).expanduser()
    lang = None if a.lang.upper() == "ALL" else a.lang.upper()
    sabs = set(_split_list(a.sabs) or []) or None
    if a.dry_run:
        dry_run(rrf_dir, lang, sabs, a.skip_indexes)
        return 0
    load(rrf_dir, a.dsn, a.release, lang, sabs, skip_indexes=a.skip_indexes,
         replace=a.replace, batch=a.batch)
    return 0


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------

class PgUMLSClient:
    """UTS-compatible client over the local PostgreSQL index.

    ``search``, ``get_concept``, ``atoms`` and ``sources`` return the same dict
    shapes as ``uts_client.UTSClient``; ``concepts_by_tui``, ``strings_like``
    and ``release`` are local extras. The connection is opened lazily on first
    use (``conn`` may be injected, e.g. a fake in tests). ``lang`` restricts
    searches to one language (``None`` = every loaded language).
    """

    def __init__(self, dsn: Optional[str] = None, conn=None,
                 lang: Optional[str] = "ENG",
                 min_similarity: float = DEFAULT_MIN_SIMILARITY):
        self.dsn = dsn
        self._conn = conn
        self.lang = lang
        self.min_similarity = min_similarity

    # -- plumbing ----------------------------------------------------------
    @property
    def conn(self):
        if self._conn is None:
            self._conn = _connect(self.dsn)
        return self._conn

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _query(self, sql: str, params=None, pre: Optional[list[tuple[str, list]]] = None) -> list[dict]:
        """Run ``pre`` statements then ``sql`` inside ONE transaction. The
        connection is autocommit, so without an explicit block each statement
        would commit on its own and a transaction-local ``set_config`` (the
        trigram threshold) would be gone before the SELECT ran."""
        import contextlib
        tx = getattr(self.conn, "transaction", None)
        block = tx() if (pre and callable(tx)) else contextlib.nullcontext()
        with block, self.conn.cursor() as cur:
            for psql, pparams in pre or []:
                cur.execute(psql, pparams)
            cur.execute(sql, params or [])
            return _rows_as_dicts(cur)

    def _similarity_pre(self) -> list[tuple[str, list]]:
        return [build_set_similarity_sql(self.min_similarity)]

    # -- UTS-compatible ----------------------------------------------------
    def search(self, term: str, search_type: str = "words",
               sabs: Optional[str] = None, page_size: int = 200,
               semantic_types: Optional[str] = None,
               partial: bool = False) -> list[dict]:
        """Same contract as ``UTSClient.search``: ``[{cui, name, root_source,
        semantic_types: [names]}]``, one row per concept."""
        if not (term or "").strip():
            return []
        sql, params = build_search_sql(term, search_type, sabs, page_size,
                                       semantic_types, partial, lang=self.lang)
        pre = self._similarity_pre() if partial else None
        out = []
        for r in self._query(sql, params, pre):
            if not r.get("name"):
                continue
            out.append({"cui": r["cui"], "name": r["name"],
                        "root_source": r.get("root_source"),
                        "semantic_types": list(r.get("semantic_types") or [])})
        return out

    def sources(self) -> list[dict]:
        """Distinct SABs -> [{sab, name, language, count}] (``name`` is the SAB
        itself: MRSAB is not loaded)."""
        sql, params = build_sources_sql()
        return [{"sab": r["sab"], "name": r["sab"], "language": r.get("language") or "",
                 "count": int(r.get("n") or 0)} for r in self._query(sql, params)]

    def get_concept(self, cui: str) -> Optional[dict]:
        sql, params = build_concept_sql(cui)
        rows = self._query(sql, params)
        if not rows or not rows[0].get("name"):
            return None
        r = rows[0]
        names = list(r.get("semantic_types") or [])
        tuis = list(r.get("tuis") or [])
        return {"cui": r["cui"], "name": r["name"],
                "root_source": r.get("root_source"),
                "semantic_types": names,
                "semantic_type_details": [{"name": n, "tui": t} for n, t in zip(names, tuis)],
                "status": None, "atom_count": int(r.get("atom_count") or 0)}

    def atoms(self, cui: str, page_size: int = 300) -> list[dict]:
        """Atoms of a CUI from ``mrconso`` -> [{sab, tty, name, language, code,
        obsolete, suppressible}] (``obsolete`` = SUPPRESS in O/E, ``suppressible``
        = SUPPRESS other than N)."""
        sql, params = build_atoms_sql(cui, page_size)
        out = []
        for r in self._query(sql, params):
            sup = (r.get("suppress") or "N").upper()
            out.append({"sab": r.get("sab"), "tty": r.get("tty"), "name": r.get("name"),
                        "language": r.get("language"), "code": r.get("code") or "",
                        "obsolete": sup in ("O", "E"), "suppressible": sup != "N"})
        return out

    def get_semantic_type(self, tui: str) -> Optional[dict]:
        """From the bundled Semantic Network reference (no database needed)."""
        from forome.gem.umls import semantic_types as ST
        t = ST.get(tui)
        if not t:
            return None
        return {"tui": t.get("tui"), "name": t.get("name"),
                "tree_number": t.get("tree_number"),
                "abbreviation": t.get("abbreviation"),
                "definition": (t.get("definition") or "").strip()}

    # -- stay on UTS -------------------------------------------------------
    def relations(self, cui: str, page_size: int = 400) -> list[dict]:
        """Not indexed locally (MRREL is not loaded); use ``UTSClient``."""
        return []

    def definitions(self, cui: str, page_size: int = 5) -> list[dict]:
        """Not indexed locally (MRDEF is not loaded); use ``UTSClient``."""
        return []

    def source_ancestors(self, sab: str, code: str, page_size: int = 120) -> list[dict]:
        """Not indexed locally (hierarchies need MRHIER); use ``UTSClient``."""
        return []

    def rollup(self, cui: str, use_sab=None, sab_allow=None,
               node_cap: int = 80) -> list[dict]:
        """Not indexed locally (hierarchies need MRHIER); use ``UTSClient``."""
        return []

    # -- local extras ------------------------------------------------------
    def concepts_by_tui(self, tuis, limit: Optional[int] = None) -> list[dict]:
        """Every concept carrying one of the TUIs -> [{cui, name, semantic_types}]."""
        if not _split_list(tuis):
            return []
        sql, params = build_concepts_by_tui_sql(tuis, limit)
        return [{"cui": r["cui"], "name": r.get("name"),
                 "root_source": r.get("root_source"),
                 "semantic_types": list(r.get("semantic_types") or [])}
                for r in self._query(sql, params)]

    def strings_like(self, term: str, min_similarity: float = DEFAULT_MIN_SIMILARITY,
                     limit: int = 200) -> list[dict]:
        """Trigram-similar atoms -> [{cui, str, sab, tty, similarity}]."""
        if not (term or "").strip():
            return []
        sql, params = build_strings_like_sql(term, limit, lang=self.lang)
        pre = [build_set_similarity_sql(min_similarity)]
        return [{"cui": r["cui"], "str": r["str"], "sab": r.get("sab"),
                 "tty": r.get("tty"), "similarity": float(r.get("similarity") or 0)}
                for r in self._query(sql, params, pre)]

    def release(self) -> Optional[dict]:
        """The most recent ``umls_release`` row (None before any load)."""
        sql, params = build_release_sql()
        rows = self._query(sql, params)
        return rows[0] if rows else None


if __name__ == "__main__":
    sys.exit(main())
