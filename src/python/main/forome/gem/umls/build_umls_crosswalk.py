#!/usr/bin/env python3
"""Build the GEM -> UMLS crosswalk by resolving each dimension/value to a
UMLS concept via the UTS REST API.

This is the harness. It reads the curated inventory
(``mapping/dimensions_inventory.yaml``), queries UMLS for each entry through a
tiered search (exact -> normalized -> words), assigns an honest status
(``mapped`` / ``review`` / ``unmapped`` / ``pending``), and writes a
machine-readable crosswalk to ``mapping/umls_crosswalk.yaml`` plus a coverage
summary. The LaTeX table is rendered separately by
``mapping/render_crosswalk_tex.py`` from that YAML.

Honesty by construction:
* Nothing is mapped without a UMLS query actually returning a concept.
* Without an API key the harness runs but every entry is ``pending`` (queried
  nothing); it does not invent CUIs.
* A query that finds candidates but no faithful exact/normalized match is
  ``review`` (candidates recorded for a curator), never silently ``mapped``.

Usage:
    # 1. verify the inventory still covers the SHACL enumerations
    python3 mapping/build_umls_crosswalk.py --check-inventory

    # 2. real run (needs a UMLS license; key in UMLS_API_KEY or --api-key)
    UMLS_API_KEY=... python3 mapping/build_umls_crosswalk.py

    # 3. offline run with no key -> all entries 'pending' (scaffold mode)
    python3 mapping/build_umls_crosswalk.py --no-key

    # 4. offline run against test fixtures (used by the unit tests)
    python3 mapping/build_umls_crosswalk.py --fixtures mapping/fixtures \
        --out mapping/umls_crosswalk.demo.yaml

Requirements: ``pyyaml``; ``requests`` for live runs; ``rdflib`` for
``--check-inventory``.
"""
from __future__ import annotations

import argparse
import os
import re
import unicodedata
from pathlib import Path

import yaml

from forome.gem.umls import semantic_types as stylib
from forome.gem.umls._paths import DATA_DIR, SCHEMA_DIR

BASE = SCHEMA_DIR.parent
INVENTORY = DATA_DIR / "dimensions_inventory.yaml"
ADJUDICATIONS = DATA_DIR / "adjudications.yaml"
SHACL = SCHEMA_DIR / "genetic_evidence.shacl.ttl"
DEFAULT_OUT = DATA_DIR / "umls_crosswalk.yaml"
CACHE_DIR = DATA_DIR / "cache"

# SHACL enum members deliberately NOT expected in the inventory:
#   - the sentinel, declared a member of every dimension class
#   - the legacy method synonyms (migrate to the renamed values)
ENUM_EXCLUDE = {
    "NOT_APPLICABLE_OR_OMITTED",
    "IN_VIVO_EXPERIMENT", "IN_VITRO_EXPERIMENT", "BIOINFORMATICS_PREDICTION",
}


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    # Fold accents to their base letters (NFD decomposition + drop combining
    # marks) before stripping non-ASCII, so e.g. "Über" -> "uber", not "ber".
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------
# Inventory loading: flatten the nested YAML into a list of entries.
# --------------------------------------------------------------------------

def load_entries(inventory_path: Path = INVENTORY) -> list[dict]:
    doc = yaml.safe_load(inventory_path.read_text())
    entries: list[dict] = []
    for dim, body in (doc.get("dimensions") or {}).items():
        axis = body.get("axis")
        if axis:
            entries.append(_entry(dim, None, "axis", axis))
        for v in body.get("values") or []:
            entries.append(_entry(dim, v["token"], "value", v))
        for v in body.get("common_values") or []:
            entries.append(_entry(dim, v["token"], "common_value", v))
    return entries


def _entry(dim: str, token, kind: str, src: dict) -> dict:
    return {
        "dimension": dim,
        "token": token,
        "kind": kind,
        "query": src["query"],
        "expect": src.get("expect", "uncertain"),
        "sab": src.get("sab"),
        "inventory_note": src.get("note"),
    }


# --------------------------------------------------------------------------
# Resolution: tiered UMLS search with honest status assignment.
# --------------------------------------------------------------------------

def resolve(client, query: str, sab: str | None, live: bool,
            stys: str | None = None) -> dict:
    if not live:
        return {"status": "pending"}

    def tier(use_sab):
        s = sab if use_sab else None
        for st in ("exact", "normalizedString", "words"):
            cands = client.search(query, search_type=st, sabs=s, semantic_types=stys)
            if cands:
                return st, cands
        return None, []

    used_sab = bool(sab)
    st, cands = tier(use_sab=True)
    if not cands and sab:
        st, cands = tier(use_sab=False)
        used_sab = False

    if not cands:
        return {"status": "unmapped"}

    top = cands[0]
    # Honesty by construction: 'mapped' requires the returned concept name to
    # actually match the query (normalized), regardless of which search tier
    # produced it. The search_type label alone is NOT a guarantee that the
    # top hit is faithful, so an 'exact'-tier hit with a mismatched name is
    # demoted to 'review', not silently mapped.
    exactish = _norm(top.get("name")) == _norm(query)
    status = "mapped" if exactish else "review"
    return {
        "status": status,
        "cui": top["cui"],
        "matched_name": top["name"],
        "root_source": top["root_source"],
        "semantic_types": top["semantic_types"],
        "search_type": st,
        "sab_filtered": used_sab,
        "sty_filtered": bool(stys),
        "candidates": [
            {k: c[k] for k in ("cui", "name", "root_source", "semantic_types")}
            for c in cands[:5]
        ],
    }


def _adj_key(dimension: str, token) -> str:
    return f"{dimension}/{token if token is not None else '(axis)'}"


def load_adjudications(path: Path | None = None) -> dict:
    """Curator decisions keyed by 'dimension/token' (or 'dimension/(axis)').
    ``path`` defaults to the CURRENT ``ADJUDICATIONS`` (resolved at call time, so
    tests/workspaces that repoint it are honoured)."""
    path = ADJUDICATIONS if path is None else path
    if not path.is_file():
        return {}
    doc = yaml.safe_load(path.read_text()) or {}
    return doc.get("adjudications", {}) or {}


def apply_adjudication(entry: dict, adj: dict, client=None) -> dict:
    """Apply a curator decision. Honest by construction: an accepted CUI is used
    only if it was among the query's candidates OR the harness can fetch it live
    from UMLS (confirming it is a real concept). The harness never fabricates a
    concept the curator merely named. A curator may also accept a concept found
    via the adjudication UI's live search; such a CUI is fetched here."""
    if adj.get("unmapped"):
        return {**entry, "status": "unmapped", "curated": True,
                "curator_note": adj.get("note")}
    cui = adj.get("accept")
    if cui:
        for c in (entry.get("candidates") or []):
            if c["cui"] == cui:
                return {**entry, "status": "mapped", "curated": True,
                        "cui": c["cui"], "matched_name": c["name"],
                        "root_source": c["root_source"],
                        "semantic_types": c["semantic_types"],
                        "curator_note": adj.get("note")}
        # Not among the query candidates: fetch it live to confirm it exists.
        concept = client.get_concept(cui) if client is not None else None
        if concept and concept.get("cui") == cui:
            return {**entry, "status": "mapped", "curated": True, "fetched": True,
                    "cui": cui, "matched_name": concept["name"],
                    "root_source": concept.get("root_source", "MTH"),
                    "semantic_types": concept.get("semantic_types", []),
                    "curator_note": adj.get("note")}
        # Cannot confirm the concept: refuse to fabricate it.
        return {**entry, "status": "review", "curated": False,
                "curator_error": f"accepted CUI {cui} not in candidates and not "
                                 f"confirmable via UMLS"}
    return entry


def build(client, live: bool, inventory_path: Path = INVENTORY,
          adjudications: dict | None = None,
          only_dims: set | None = None) -> dict:
    """Resolve the whole inventory. Each dimension AXIS maps to a UMLS semantic
    type (from adjudication accept_sty, else the inventory's semantic_type), and
    that type's subtree constrains the search for the dimension's VALUE concepts
    -- so axis and values reconcile by construction (a value is only ever mapped
    within its axis's semantic branch).

    ``only_dims`` restricts resolution to those dimensions (a scoped rebuild);
    the returned doc then contains only their entries, and the caller is
    responsible for merging into a full crosswalk."""
    if adjudications is None:
        adjudications = load_adjudications()
    doc = yaml.safe_load(inventory_path.read_text())
    out_entries = []
    for dim, body in (doc.get("dimensions") or {}).items():
        if only_dims is not None and dim not in only_dims:
            continue
        axis = body.get("axis")
        axis_adj = adjudications.get(_adj_key(dim, None)) or {}
        if axis_adj.get("unmapped"):
            axis_sty = None                                   # curator: axis untyped
        else:
            axis_sty = axis_adj.get("accept_sty") or (axis or {}).get("semantic_type")
        stys = stylib.filter_param(axis_sty)                  # value-search filter

        if axis is not None:
            e = _entry(dim, None, "axis", axis)
            if not live:
                e["status"] = "pending"
            elif axis_sty:
                sty = stylib.get(axis_sty)
                if sty:
                    e.update({"status": "mapped",
                              "curated": bool(axis_adj.get("accept_sty")),
                              "sty_tui": sty["tui"], "sty_name": sty["name"],
                              "sty_tree": sty.get("tree_number"),
                              "curator_note": axis_adj.get("note")})
                else:
                    e.update({"status": "review",
                              "curator_error": f"semantic type {axis_sty} not in "
                              "semantic_types.yaml (run fetch_semantic_network.py)"})
            else:
                e["status"] = "unmapped"
                if axis_adj.get("unmapped"):
                    e.update({"curated": True, "curator_note": axis_adj.get("note")})
            out_entries.append(e)

        for kind, seq in (("value", "values"), ("common_value", "common_values")):
            for v in body.get(seq) or []:
                e = _entry(dim, v["token"], kind, v)
                res = resolve(client, e["query"], e.get("sab"), live, stys=stys)
                entry = {**e, **res}
                adj = adjudications.get(_adj_key(dim, v["token"]))
                if adj and live:
                    entry = apply_adjudication(entry, adj, client=client)
                out_entries.append(entry)

    counts = {s: 0 for s in ("mapped", "review", "unmapped", "pending")}
    for e in out_entries:
        counts[e["status"]] += 1  # KeyError surfaces any unexpected status
    counts["curated"] = sum(1 for e in out_entries if e.get("curated"))
    counts["axis_typed"] = sum(1 for e in out_entries if e.get("sty_tui"))
    return {
        "meta": {
            "generated_by": "mapping/build_umls_crosswalk.py",
            "source_inventory": "mapping/dimensions_inventory.yaml",
            "live": live,
            "total": len(out_entries),
            "counts": counts,
        },
        "entries": out_entries,
    }


# --------------------------------------------------------------------------
# Inventory <-> SHACL drift check.
# --------------------------------------------------------------------------

def shacl_enum_members() -> set[str]:
    import rdflib
    g = rdflib.Graph().parse(str(SHACL))
    GEM = "https://w3id.org/genetic-evidence-model/"
    enum_classes = {GEM + c for c in (
        "KnowledgeDomain", "Method", "TargetType", "Resolution", "Credibility",
        "PhenotypeScale", "VariantAscertainment", "MeasurementTarget",
        "GeneRelation", "KnockoutType", "Penetrance")}
    rdf_type = rdflib.RDF.type
    members = set()
    for s, _, o in g.triples((None, rdf_type, None)):
        if str(o) in enum_classes and str(s).startswith(GEM):
            members.add(str(s)[len(GEM):])
    return members - ENUM_EXCLUDE


# Dimensions whose values are intentionally NOT in the SHACL enumerations
# (open / not schema-enumerated): the harness expects inventory tokens here
# that have no SHACL member.
OPEN_DIMS = {"subdomain", "mode_of_inheritance"}


def check_inventory() -> int:
    members = shacl_enum_members()
    entries = load_entries()
    inv_tokens = {str(e["token"]) for e in entries if e["token"] is not None}
    missing = sorted(members - inv_tokens)
    # Extra inventory tokens are expected for the open dimensions; any OTHER
    # extra (a token that is neither a SHACL member nor in an open dimension)
    # is surfaced as a warning so a stray/typo'd token does not hide.
    open_tokens = {str(e["token"]) for e in entries
                   if e["token"] is not None and e["dimension"] in OPEN_DIMS}
    extra = sorted((inv_tokens - members) - open_tokens)
    if missing:
        print("INVENTORY DRIFT: SHACL enum members not covered by the inventory:")
        for m in missing:
            print(f"  - {m}")
        return 1
    print(f"Inventory covers all {len(members)} SHACL enum members "
          f"(excluding sentinel + legacy synonyms).")
    if extra:
        print(f"WARNING: {len(extra)} inventory token(s) outside both the SHACL "
              f"enums and the open dimensions ({', '.join(sorted(OPEN_DIMS))}):")
        for e in extra:
            print(f"  - {e}")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _make_client(args):
    if args.check_inventory:
        return None, False
    if args.fixtures:
        from forome.gem.umls.uts_client import FixtureClient
        return FixtureClient(Path(args.fixtures)), True
    key = args.api_key or os.environ.get("UMLS_API_KEY", "")
    if key and not args.no_key:
        from forome.gem.umls.uts_client import UTSClient
        return UTSClient(key, cache_dir=CACHE_DIR), True
    from forome.gem.umls.uts_client import NullClient
    return NullClient(), False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api-key", help="UMLS UTS API key (else $UMLS_API_KEY).")
    ap.add_argument("--no-key", action="store_true",
                    help="Force scaffold mode: run with no UMLS query (all 'pending').")
    ap.add_argument("--fixtures", help="Directory of canned UTS responses (offline tests).")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output crosswalk YAML path.")
    ap.add_argument("--check-inventory", action="store_true",
                    help="Only verify the inventory still covers the SHACL enums; do not query.")
    args = ap.parse_args(argv)

    if args.check_inventory:
        return check_inventory()

    client, live = _make_client(args)
    doc = build(client, live)
    Path(args.out).write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100))

    c = doc["meta"]["counts"]
    print(f"Wrote {args.out}")
    print(f"  total={doc['meta']['total']}  mapped={c['mapped']}  "
          f"review={c['review']}  unmapped={c['unmapped']}  pending={c['pending']}"
          f"  (curated={c.get('curated', 0)})")
    if not live:
        print("  (scaffold mode: no UMLS key supplied -> all entries 'pending'. "
              "Set UMLS_API_KEY and rerun to resolve concepts.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
