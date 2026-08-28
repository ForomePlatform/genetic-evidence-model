#!/usr/bin/env python3
"""GEM Mapping Studio: local, Metathesaurus-integrated adjudication UI + axis
builder for the UMLS crosswalk.

A small localhost web app with two jobs, over one mapping directory (the
"workspace"). Navigation follows the model's own hierarchy: core dimensions
first in canonical order, then conditional dimensions grouped by activation
rule, then candidates -- driven by the inventory's per-dimension tier / order /
activation metadata (missing tier defaults to core).

* Build / modify AXES. An axis maps a GEM dimension to a UMLS *semantic type*
  (TUI); the type's subtree becomes the value-search filter for that dimension.
  "+ New axis" constructs one from scratch (search / browse the Semantic Network,
  pick the most-specific type, see its subtree and the filter breadth it
  implies); clicking an existing axis modifies it. Axes are written to the
  workspace's dimensions_inventory.yaml -- so the tool works against an EMPTY
  directory (build from scratch) or a populated one (modify).

* Adjudicate VALUES. For each value it shows the GEM meaning (from
  dimensions.md), the query used, the current decision, and the candidate
  concepts. You can search the UMLS Metathesaurus live, read each concept's
  definition, semantic type, vocabularies, is_a hierarchy and rollup, then
  Accept a concept, mark it Unmapped, or Clear. Choices are written to the
  workspace's adjudications.yaml; a Rebuild button reruns the harness.

Concept-level relations (is_a, part_of, gene_mapped_to_disease, ...) are shown
only for value candidates -- they are concept-to-concept edges and do not apply
to axes, whose structure is the Semantic Network, not the Metathesaurus.

Honest by construction: accepting a concept found via search (not among the
query's candidates) makes the harness fetch it live from UMLS on rebuild to
confirm it is a real concept -- the harness never records a CUI it cannot
resolve.

It runs locally (not a hosted artifact) because it must reach the licensed UTS
API with your key and write files. The key is read from UMLS_API_KEY or .envrc
and never sent to the browser; the browser calls local /api/* endpoints that
proxy UMLS.

Usage:
    export UMLS_API_KEY=...            # or have it in .envrc; optional -- axis
                                       # construction works offline
    gem-umls-adjudicate [--data-dir DIR] [--port N] [--no-browser]
        DIR is a mapping workspace (inventory / crosswalk / adjudications); it
        may be empty. Defaults to the repo's data/umls, or $GEM_DATA_DIR.
Requirements: pyyaml, requests (stdlib http.server otherwise).
"""
from __future__ import annotations

import json
import os
import re
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import yaml

from forome.gem.umls import build_umls_crosswalk as H
from forome.gem.umls import semantic_types as stylib
from forome.gem.umls.uts_client import UTSClient, NullClient
from forome.gem.umls._paths import DATA_DIR, SCHEMA_DIR

CROSSWALK = DATA_DIR / "umls_crosswalk.yaml"
DIMS_MD = SCHEMA_DIR / "dimensions.md"
PREF_DEF_SOURCES = ["MSH", "NCI", "NCI_NCI-GLOSS", "SNOMEDCT_US", "HPO", "CSP",
                    "MDR", "AIR", "PDQ", "GO", "MTH"]
NON_ENGLISH = ("CZE", "DUT", "FRE", "GER", "SPA", "ITA", "POR", "JPN", "RUS",
               "SCR", "SWE", "FIN", "NOR", "DAN", "HUN", "POL", "GRE", "KOR")

# rela values that are lexical/synonym bookkeeping rather than a concept-to-
# concept relationship -- filtered out of the "other relations" view.
_LEXICAL_RELA = frozenset({
    "has_permuted_term", "permuted_term_of", "translation_of", "has_translation",
    "has_transliterated_form", "transliterated_form_of",
    "has_expanded_form", "expanded_form_of", "has_alias", "alias_of",
    "has_prev_name", "prev_name_of", "has_sort_version", "sort_version_of",
    "has_entry_version", "entry_version_of", "has_common_name", "common_name_of",
    "has_permuted_term_of", "has_multi_level_category", "mth_expanded_form_of",
})

ADJ_HEADER = [
    "# Curator adjudications for the UMLS crosswalk review/unmapped entries.",
    "# Applied by build_umls_crosswalk.py AFTER querying. 'accept' is used only if the",
    "# CUI was among the query's candidates OR the harness can fetch it live from UMLS;",
    "# the harness never fabricates a concept the curator merely named. 'unmapped: true'",
    "# records a considered 'no faithful UMLS concept' (honest finding). Edited via",
    "# mapping/adjudicate_ui.py.",
]


def api_key() -> str:
    k = os.environ.get("UMLS_API_KEY", "")
    if k:
        return k
    envrc = H.BASE / ".envrc"
    if envrc.is_file():
        for line in envrc.read_text().splitlines():
            m = re.match(r"\s*export\s+UMLS_API_KEY=(.+)", line)
            if m:
                return m.group(1).strip().strip("\"'")
    return ""


def load_meanings() -> dict:
    """token -> meaning, parsed from the markdown tables in dimensions.md."""
    m = {}
    if DIMS_MD.is_file():
        for line in DIMS_MD.read_text().splitlines():
            mt = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|\s*$", line)
            if mt:
                m.setdefault(mt.group(1).strip(), mt.group(2).strip())
    return m


MEANINGS = load_meanings()


def _dimensions() -> dict:
    """The inventory's dimensions block (empty if the workspace has no inventory)."""
    if H.INVENTORY.is_file():
        return (yaml.safe_load(H.INVENTORY.read_text()) or {}).get("dimensions") or {}
    return {}


def load_state() -> dict:
    """Assemble the UI state from whatever the workspace has. Axes come from the
    inventory (so they exist even before any crosswalk is built), values from the
    crosswalk when present. Every file is optional -- an empty workspace yields
    no dimensions, ready for the axis builder to create the first one."""
    dims = _dimensions()
    adj = H.load_adjudications()
    doc = yaml.safe_load(CROSSWALK.read_text()) if CROSSWALK.is_file() else None

    def dim_axis_tui(dim):
        a = adj.get(H._adj_key(dim, None)) or {}
        if a.get("unmapped"):
            return None
        return a.get("accept_sty") or (dims.get(dim, {}).get("axis") or {}).get("semantic_type")

    # value entries from the crosswalk, grouped by dimension
    values_by_dim: dict = {}
    if doc:
        for e in doc.get("entries", []):
            if e.get("kind") == "axis":
                continue
            values_by_dim.setdefault(e["dimension"], []).append(e)

    # Tiered ordering: core dimensions first in the model's canonical order,
    # then conditional (grouped by activation via their order values), then
    # candidate -- never the alphabet. A dimension without explicit tier
    # metadata is treated as core (and flagged so the UI can warn).
    TIER_RANK = {"core": 0, "conditional": 1, "candidate": 2}

    def dim_sort_key(d):
        block = dims.get(d) or {}
        tier = block.get("tier") or "core"
        try:
            order = int(block.get("order", 999))
        except (TypeError, ValueError):   # hand-edited inventory: "20", blank, ...
            order = 999
        return (TIER_RANK.get(tier, 0), order, d)

    entries = []
    for dim in sorted(set(dims) | set(values_by_dim), key=dim_sort_key):
        block = dims.get(dim) or {}
        axis = block.get("axis") or {}
        akey = H._adj_key(dim, None)
        aadj = adj.get(akey) or {}
        eff = dim_axis_tui(dim)
        filt = stylib.filter_param(eff)
        sty = stylib.get(eff) if eff else None
        # axis entry (from the inventory)
        entries.append({
            "key": akey, "dimension": dim, "token": None, "kind": "axis",
            "query": axis.get("query") or "",
            "meaning": axis.get("note") or MEANINGS.get(dim) or "",
            "status": "mapped" if eff else "review",
            "curated": bool(aadj.get("accept_sty") or aadj.get("unmapped")),
            "fetched": False, "cui": None, "matched_name": None,
            "semantic_types": [], "root_source": None, "candidates": [],
            "sty_tui": eff, "sty_name": sty.get("name") if sty else None,
            "sty_tree": sty.get("tree_number") if sty else None,
            "axis_query": axis.get("query") or "", "axis_note": axis.get("note") or "",
            "in_inventory": dim in dims,
            "tier": block.get("tier") or "core",
            "tier_explicit": "tier" in block,
            "order": block.get("order", 999),
            "activation": block.get("activation"),
            "dim_sty_tui": eff, "dim_sty_filter": filt,
            "decision": ("accept_sty" if aadj.get("accept_sty")
                         else "unmapped" if aadj.get("unmapped") else None),
            "decision_cui": None, "decision_sty": aadj.get("accept_sty"),
            "note": aadj.get("note"), "error": None,
        })
        # value entries for this dimension (from the crosswalk)
        for e in values_by_dim.get(dim, []):
            key = H._adj_key(e["dimension"], e["token"])
            a = adj.get(key) or {}
            entries.append({
                "key": key, "dimension": e["dimension"], "token": e["token"],
                "kind": e["kind"], "query": e["query"],
                "meaning": MEANINGS.get(str(e["token"])) or e.get("inventory_note") or "",
                "status": e["status"], "curated": bool(e.get("curated")),
                "fetched": bool(e.get("fetched")),
                "cui": e.get("cui"), "matched_name": e.get("matched_name"),
                "semantic_types": e.get("semantic_types") or [],
                "root_source": e.get("root_source"),
                "candidates": e.get("candidates") or [],
                "sty_tui": e.get("sty_tui"), "sty_name": e.get("sty_name"),
                "sty_tree": e.get("sty_tree"),
                "dim_sty_tui": eff, "dim_sty_filter": filt,
                "decision": ("accept" if a.get("accept") else
                             "accept_sty" if a.get("accept_sty") else
                             "unmapped" if a.get("unmapped") else None),
                "decision_cui": a.get("accept"), "decision_sty": a.get("accept_sty"),
                "note": a.get("note"), "error": e.get("curator_error"),
            })

    if doc:
        counts = doc["meta"]["counts"]
    else:
        vals = [e for e in entries if e["kind"] != "axis"]
        counts = {"total": len(vals),
                  "mapped": sum(e["status"] == "mapped" for e in vals),
                  "unmapped": sum(e["status"] == "unmapped" for e in vals),
                  "review": sum(e["status"] == "review" for e in vals),
                  "curated": sum(bool(e["curated"]) for e in vals)}
    return {"entries": entries, "counts": counts,
            "workspace": str(DATA_DIR), "dimensions": sorted(dims)}


def write_adjudications(adj: dict) -> None:
    L = list(ADJ_HEADER) + ["adjudications:"]
    for key in sorted(adj):
        v = adj[key]
        note = (v.get("note") or "").replace('"', "'")
        if v.get("accept"):
            L.append(f'  "{key}": {{accept: {v["accept"]}, note: "{note}"}}')
        elif v.get("accept_sty"):
            L.append(f'  "{key}": {{accept_sty: {v["accept_sty"]}, note: "{note}"}}')
        elif v.get("unmapped"):
            L.append(f'  "{key}": {{unmapped: true, note: "{note}"}}')
    H.ADJUDICATIONS.write_text("\n".join(L) + "\n")


def save_axis(dimension: str, semantic_type=None, query=None, note=None,
              tier=None, activation=None, order=None) -> dict:
    """Create or update a dimension's axis block in the workspace inventory,
    creating the inventory file (and directory) if absent. This is how a new
    axis is constructed from scratch and how an existing one is modified.
    ``tier`` (core|conditional|candidate), ``activation`` and ``order`` are
    block-level presentation metadata driving the tiered navigation.
    Returns the resulting axis block."""
    dimension = (dimension or "").strip()
    if not dimension:
        raise ValueError("a dimension name is required")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", dimension):
        raise ValueError("dimension name must use letters, digits, _ or -")
    if semantic_type and not stylib.get(semantic_type):
        raise ValueError(f"unknown semantic type {semantic_type!r}")
    if tier and tier not in ("core", "conditional", "candidate"):
        raise ValueError(f"unknown tier {tier!r}")
    if order is not None:
        try:
            order = int(order)
        except (TypeError, ValueError):
            raise ValueError(f"order must be an integer, got {order!r}")
    inv = yaml.safe_load(H.INVENTORY.read_text()) if H.INVENTORY.is_file() else {}
    inv = inv or {}
    block = inv.setdefault("dimensions", {}).setdefault(dimension, {})
    if tier:
        block["tier"] = tier
    if order is not None:
        block["order"] = order
    if activation is not None:
        if activation:
            block["activation"] = activation
        else:
            block.pop("activation", None)
    axis = block.setdefault("axis", {})
    if query is not None:
        axis["query"] = query
    if note is not None:
        axis["note"] = note
    if semantic_type:
        axis["semantic_type"] = semantic_type
    H.INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    H.INVENTORY.write_text(
        yaml.safe_dump(inv, sort_keys=False, allow_unicode=True, width=100))
    return axis


def order_defs(defs: list) -> list:
    eng = [d for d in defs if not (d.get("source") or "").endswith(NON_ENGLISH)]
    pool = eng or defs

    def pri(d):
        s = d.get("source", "")
        return PREF_DEF_SOURCES.index(s) if s in PREF_DEF_SOURCES else 99
    return sorted(pool, key=pri)[:3]


def concept_evidence(cui: str, axis_tui: str | None = None,
                     english_only: bool = True) -> dict:
    """Per-CUI evidence for the adjudication UI: most-specific semantic type
    with STN and the path up to the axis type, the source vocabularies as
    SAB/STR atom rows (English only by default), and is_a relations one per row
    with direction. Rollup is fetched separately (on demand) via /api/rollup."""
    c = client.get_concept(cui)
    if not c:
        return {"error": "concept not found"}
    atoms = client.atoms(cui)
    if english_only:
        atoms = [a for a in atoms if (a.get("language") or "ENG") == "ENG"]
    atom_rows = sorted(({"sab": a["sab"], "str": a["name"], "tty": a["tty"],
                         "code": a["code"],
                         "obsolete": a["obsolete"] or a["suppressible"]}
                        for a in atoms if a["sab"]),
                       key=lambda x: (x["sab"], x["tty"] or "", x["str"] or ""))
    sabs = sorted({a["sab"] for a in atoms if a["sab"]})
    # most-specific semantic type + STN + path to the axis type
    details = c.get("semantic_type_details") or []
    tuis = [d["tui"] for d in details if d.get("tui")]
    spec = stylib.most_specific(tuis) if tuis else None
    sty_path = stylib.path_to(spec, axis_tui) if spec else []
    under_axis = bool(axis_tui and sty_path and sty_path[-1]["tui"] == axis_tui)
    axis_sty = stylib.get(axis_tui) if axis_tui else None
    # relations. A source counts as English iff it contributed an English atom
    # above -- exactly the SAB set of the English vocabularies subtable, robust
    # to the many language mirrors (MSHCZE, SCTSPA, MDRARA, ...) a suffix list
    # would miss.
    rels = client.relations(cui)
    sab_ok = set(sabs)

    def _agg(pred, extra):
        """Collapse matching relations to one row per related concept. The id
        is a CUI for CUI-level relations, otherwise the source code."""
        m: dict = {}
        for r in rels:
            rid = r.get("related_code") or r.get("related_cui")
            if not rid or not pred(r):
                continue
            sab = r["sab"]
            if english_only and sab not in sab_ok:
                continue
            e = m.setdefault(rid, {"code": rid, "cui": r.get("related_cui"),
                             "name": r["related_name"], "sabs": set(), **extra(r)})
            if sab:
                e["sabs"].add(sab)
        return [{**v, "sabs": sorted(v["sabs"])} for v in m.values()]

    # is_a hierarchy -- keyed on rela, NOT rel: only isa/inverse_isa edges are a
    # true taxonomy. Note UMLS orientation: rela=="isa" means this concept isa
    # the related one, i.e. the related concept is the PARENT (up); inverse_isa
    # is the child (down). MeSH-style PAR/CHD with empty rela is a thematic tree,
    # not is_a, and is intentionally excluded here (and from the rollup).
    isa_up = _agg(lambda r: r["rela"] == "isa", lambda r: {"dir": "up"})[:25]
    isa_down = _agg(lambda r: r["rela"] == "inverse_isa", lambda r: {"dir": "down"})[:25]

    # other meaningful relations, grouped by their (labelled) rela -- the
    # semantically rich edges a curator wants (gene_mapped_to_disease,
    # has_allelic_variant, part_of, mapped_to, ...). Skip is_a (shown above) and
    # lexical/synonym bookkeeping (permuted/translation/alias/expanded forms).
    other = _agg(lambda r: (r["rela"] and r["rela"] not in ("isa", "inverse_isa")
                            and r["rel"] != "SY" and r["rela"] not in _LEXICAL_RELA),
                 lambda r: {"rela": r["rela"]})
    groups: dict = {}
    for row in other:
        groups.setdefault(row["rela"], []).append(row)
    other_relations = [{"rela": k, "n": len(v), "items": v[:12]}
                       for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))][:20]

    return {"cui": cui, "name": c["name"], "status": c.get("status"),
            "atom_count": c.get("atom_count"), "semantic_types": details,
            "most_specific_tui": spec, "sty_path": sty_path,
            "under_axis": under_axis,
            "axis_sty": ({"tui": axis_sty["tui"], "name": axis_sty["name"],
                          "stn": axis_sty.get("tree_number")} if axis_sty else None),
            "sabs": sabs, "atom_rows": atom_rows[:80],
            "relations": isa_up + isa_down, "other_relations": other_relations}


client = None  # set in main()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")  # never serve a stale page
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/":
                return self._send(200, HTML, "text/html; charset=utf-8")
            if u.path == "/api/state":
                return self._send(200, json.dumps(load_state()))
            if u.path == "/api/search":
                term = (q.get("string") or [""])[0]
                sab = (q.get("sabs") or [""])[0] or None
                stys = (q.get("stys") or [""])[0] or None
                res = client.search(term, search_type="words", sabs=sab, semantic_types=stys)
                return self._send(200, json.dumps({"results": res}))
            if u.path == "/api/rollup":
                cui = (q.get("cui") or [""])[0]
                sab = (q.get("use_sab") or [""])[0] or None
                # roll up within English is_a vocabularies only: those that gave
                # this concept an English atom AND assert a direct is_a parent
                # (MeSH asserts a thematic tree, no is_a, so it is never offered).
                eng = {a["sab"] for a in client.atoms(cui)
                       if a.get("sab") and (a.get("language") or "ENG") == "ENG"}
                isa_sabs = sorted({r["sab"] for r in client.relations(cui)
                                   if r["rela"] == "isa" and r["sab"] in eng})
                roll = client.rollup(cui, use_sab=sab, sab_allow=set(isa_sabs))
                return self._send(200, json.dumps({"rollup": roll, "sabs": isa_sabs}))
            if u.path == "/api/semantictypes":
                return self._send(200, json.dumps({"types": [
                    {"tui": t["tui"], "name": t["name"], "tree": t.get("tree_number"),
                     "definition": (t.get("definition") or "")[:200]}
                    for t in stylib.all_types()]}))
            if u.path == "/api/concept":
                cui = (q.get("cui") or [""])[0]
                axis = (q.get("axis") or [""])[0] or None
                ev = concept_evidence(cui, axis)
                defs = order_defs(client.definitions(cui))
                return self._send(200, json.dumps({"evidence": ev, "definitions": defs}))
        except Exception as ex:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(ex)}))
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        ln = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(ln) or b"{}")
            u = urlparse(self.path)
            if u.path == "/api/decide":
                adj = H.load_adjudications()
                key, verdict = data["key"], data.get("verdict")
                if verdict == "accept":
                    adj[key] = {"accept": data["cui"],
                                "note": data.get("note") or "curator-accepted via UI"}
                elif verdict == "accept_sty":
                    adj[key] = {"accept_sty": data["tui"],
                                "note": data.get("note") or "axis semantic type set via UI"}
                elif verdict == "unmapped":
                    adj[key] = {"unmapped": True,
                                "note": data.get("note") or "no faithful UMLS concept (curator)"}
                elif verdict == "clear":
                    adj.pop(key, None)
                else:
                    return self._send(400, json.dumps({"error": "bad verdict"}))
                write_adjudications(adj)
                return self._send(200, json.dumps({"ok": True}))
            if u.path == "/api/axis":
                try:
                    axis = save_axis(data.get("dimension"),
                                     semantic_type=data.get("semantic_type") or None,
                                     query=data.get("query"), note=data.get("note"),
                                     tier=data.get("tier") or None,
                                     activation=data.get("activation"),
                                     order=data.get("order"))
                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                # the inventory is now authoritative for this axis's type; drop a
                # stale accept_sty adjudication override so it takes effect.
                adj = H.load_adjudications()
                akey = H._adj_key((data.get("dimension") or "").strip(), None)
                if (adj.get(akey) or {}).get("accept_sty"):
                    adj.pop(akey, None)
                    write_adjudications(adj)
                return self._send(200, json.dumps({"ok": True, "axis": axis}))
            if u.path == "/api/rebuild":
                doc = H.build(client, live=True)
                CROSSWALK.write_text(yaml.safe_dump(doc, sort_keys=False,
                                                    allow_unicode=True, width=100))
                return self._send(200, json.dumps({"ok": True, "counts": doc["meta"]["counts"]}))
        except Exception as ex:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(ex)}))
        self._send(404, json.dumps({"error": "not found"}))


HTML = r'''<!doctype html><html><head><meta charset="utf-8">
<title>GEM Mapping Studio</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" media="print" onload="this.media='all'">
<style>
:root{
  --paper:#f5f3ee;--rail:#f0ede4;--card:#fdfcf9;--ink:#23201a;--mut:#736d5f;--faint:#8a8474;
  --line:#e4e0d3;--hair:#f0ece0;--accent:#155e68;--accent-soft:#e2edee;--accent-bd:#b9d2d5;
  --ok:#23663f;--ok-bg:#e2efe5;--ok-bd:#c8e0cf;--ok-dot:#3f9463;
  --rev:#8a5f0c;--rev-bg:#f6ecd3;--rev-bd:#e8d9ab;--rev-dot:#d9a13a;
  --un:#6d675a;--un-bg:#eeeade;--un-bd:#ddd7c6;--un-dot:#cbc5b4;
  --warn:#9a5a1d;--danger:#9a4633;--link:#22557e;--link-bg:#e2ebf3;
  --serif:'Source Serif 4',Georgia,serif;
  --sans:'IBM Plex Sans','Helvetica Neue',Arial,sans-serif;
  --mono:'IBM Plex Mono',Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;font:13.5px/1.45 var(--sans);color:var(--ink);background:var(--paper);display:flex;height:100vh;overflow:hidden}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
button{font:inherit;font-size:12.5px;font-weight:600;padding:6px 13px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:7px;cursor:pointer}
button:hover{background:#f4f1e8}
button.primary{background:var(--accent);color:#f6f3ea;border-color:var(--accent)}
button.primary:hover{background:#0f454d}
button.ok{background:var(--card);color:var(--ok);border-color:var(--ok-bd)}
button.warn{background:var(--card);color:var(--rev);border-color:var(--rev-bd)}
button.mini{font-size:11px;font-weight:500;padding:2px 8px}
input,select,textarea{font:inherit;border:1px solid #d8d3c3;background:#fff;border-radius:7px;padding:6px 10px;color:var(--ink)}
input:focus,textarea:focus{outline:1.5px solid var(--accent-bd)}
textarea{width:100%;min-height:44px}
/* ---- rail ---- */
#rail{width:280px;flex-shrink:0;display:flex;flex-direction:column;background:var(--rail);border-right:1px solid var(--line)}
#brand{display:flex;align-items:center;gap:10px;padding:18px 18px 12px;cursor:pointer}
#brand .nm{font-family:var(--serif);font-size:16px;font-weight:700}
#brand .ws{font-family:var(--mono);font-size:10.5px;color:var(--faint);word-break:break-all}
#nav{flex:1;overflow:auto;padding:4px 0 8px}
.tierhdr{padding:10px 18px 4px;font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--faint)}
.nitem{display:flex;align-items:center;gap:8px;padding:5px 18px;cursor:pointer}
.nitem:hover{background:#e9e5d8}
.nitem.active{background:#e9e5d8;border-left:3px solid var(--accent);padding-left:15px}
.nitem .nm{font-size:13px;font-weight:500;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nitem.active .nm{font-weight:600}
.nitem .fr{margin-left:auto;font-family:var(--mono);font-size:11px;color:var(--faint);white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;flex:0 0 8px}
.dot.mapped{background:var(--ok-dot)}.dot.review,.dot.part{background:var(--rev-dot)}.dot.unmapped,.dot.none{background:var(--un-dot)}
.ghdr{display:flex;align-items:center;gap:7px;padding:4px 18px;color:var(--mut);cursor:pointer;font-family:var(--mono);font-size:10.5px}
.ghdr:hover{background:#e9e5d8}
.ghdr .cnt{margin-left:auto;font-size:10.5px}
.gkid{padding-left:34px}
.gkid .nm{font-size:12.5px;font-weight:400}
.condchip{font-size:9.5px;font-weight:600;color:var(--faint);border:1px solid #d8d3c3;border-radius:999px;padding:0 5px;white-space:nowrap}
#railfoot{padding:12px 18px;border-top:1px solid var(--line)}
#railfoot button{width:100%;color:var(--accent);border-color:var(--accent);background:transparent}
.navempty{padding:2px 18px;font-size:12px;color:var(--faint);font-style:italic}
/* ---- main ---- */
#main{flex:1;display:flex;flex-direction:column;min-width:0}
#head{padding:20px 32px 0}
.crumb{font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--faint);text-transform:uppercase}
.crumb a{color:var(--faint)}.crumb a:hover{color:var(--accent)}
.titlerow{display:flex;align-items:center;gap:12px;margin-top:4px;flex-wrap:wrap}
.title-serif{font-family:var(--serif);font-size:24px;font-weight:700}
.title-mono{font-family:var(--mono);font-size:21px;font-weight:500}
.titlerow .spacer{flex:1}
#msg{font-size:12px;color:var(--mut)}
.orient{margin-top:6px;font-size:13px;color:var(--mut);max-width:780px}
.orient b{color:var(--ink)}
#content{flex:1;overflow:auto;padding:16px 32px 28px}
/* ---- shared bits ---- */
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 17px;margin-bottom:14px}
.card h3{margin:0 0 8px;font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--faint);text-transform:uppercase}
.card h3 .hint{font-weight:400;letter-spacing:0;text-transform:none;font-size:11.5px;color:#a29b89;font-style:italic;margin-left:8px}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;border-radius:999px;padding:1px 9px;border:1px solid var(--line);color:var(--mut);vertical-align:1px}
.chip.tier{color:var(--accent);background:var(--accent-soft);border-color:var(--accent-bd);letter-spacing:.06em;font-size:10.5px}
.chip.st-mapped{color:var(--ok);background:var(--ok-bg);border-color:var(--ok-bd)}
.chip.st-review{color:var(--rev);background:var(--rev-bg);border-color:var(--rev-bd)}
.chip.st-unmapped{color:var(--un);background:var(--un-bg);border-color:var(--un-bd)}
.chip.tui{font-family:var(--mono);font-weight:500;color:var(--link);background:var(--link-bg);border-color:transparent}
.chip.warnc{color:var(--warn);background:#f7ecdd;border-color:#eddabb}
.mono{font-family:var(--mono)}.mut{color:var(--mut)}.mini{font-size:11.5px;color:var(--faint)}
.cui{font-family:var(--mono);font-size:12px;color:var(--link)}
.stn{font-family:var(--mono);color:var(--faint)}
.sab{font-family:var(--mono);font-size:10px;color:var(--faint);border:1px solid var(--un-bd);border-radius:999px;padding:0 5px}
.warnsvg{color:var(--warn)}
.bar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--un-bd)}
.bar .m{background:var(--ok-dot)}.bar .r{background:var(--rev-dot)}.bar .u{background:var(--un-bd)}
.minibar{display:inline-flex;width:78px;height:6px;border-radius:3px;overflow:hidden;background:var(--hair);vertical-align:1px}
.legend{display:flex;align-items:center;gap:14px;margin-top:8px;font-size:12px;color:var(--mut);flex-wrap:wrap}
.legend b{color:var(--ink)}
.ldot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:5px;vertical-align:-1px}
/* home tables */
.hrow{display:grid;grid-template-columns:200px minmax(0,1fr) 145px 104px;align-items:center;column-gap:12px;padding:8px 0;border-top:1px solid var(--hair);cursor:pointer;font-size:12.5px}
.hrow:hover{background:#f4f1e8;margin:0 -17px;padding-left:17px;padding-right:17px}
.hrow .dn{font-family:var(--mono);font-size:12.5px;font-weight:500;display:flex;align-items:center;gap:7px;min-width:0}
.hrow .st{justify-self:end}
.condline{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;margin-top:8px}
.condline .act{font-family:var(--mono);font-size:10.5px;color:var(--faint)}
.condline a{color:var(--ink)}.condline a:hover{color:var(--accent)}
.condline .f{font-family:var(--mono);font-size:10.5px;color:var(--mut)}
/* values table */
.vt{border-collapse:collapse;width:100%;font-size:12.5px}
.vt th{text-align:left;color:var(--faint);font-weight:600;font-size:10.5px;letter-spacing:.07em;border-bottom:1px solid var(--line);padding:4px 10px 4px 0;white-space:nowrap}
.vt td{padding:5px 10px 5px 0;border-bottom:1px solid var(--hair);vertical-align:middle}
.vt tr.vrow{cursor:pointer}
.vt tr.vrow:hover td{background:#f4f1e8}
.vt .tk{font-family:var(--mono);font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:250px}
/* axis card */
.axgrid{display:flex;gap:0;margin:0 -17px}
.axgrid>div{flex:1;padding:0 17px}
.axgrid>div:first-child{border-right:1px dashed var(--line)}
.axtype .tnm{font-family:var(--serif);font-size:17px;font-weight:600}
.axrow{display:flex;gap:8px;align-items:center;margin:7px 0}
.axrow label{width:74px;color:var(--mut);font-size:12px;text-align:right;flex-shrink:0}
.axrow input,.axrow select{flex:1;min-width:0}
.axrow input[readonly]{background:var(--hair);color:var(--mut)}
.stnbox{margin-top:8px;font-family:var(--mono);font-size:11.5px;line-height:1.7;color:var(--mut)}
/* candidates + evidence (value view) */
.cand{border:1px solid var(--line);border-radius:9px;padding:9px 12px;margin-bottom:8px;background:var(--card)}
.cand.acc{border-color:var(--ok-bd);background:#f2f8f3;border-width:1.5px}
.cand .row{display:flex;align-items:center;gap:8px}.cand .row .n{flex:1;font-weight:500}
.sty{font-size:11px;color:var(--faint);margin-top:2px}
.def{margin-top:6px;font-size:12.5px;color:#3d382e;background:var(--hair);border-radius:6px;padding:7px 10px;display:none}
.def.show{display:block}
.searchbar{display:flex;gap:8px;margin-bottom:8px}.searchbar input{flex:1}
.curbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px}
.now{font-size:13px}
.badge{font-size:10px;font-weight:600;padding:1px 6px;border-radius:999px;background:var(--ok-bg);color:var(--ok);border:1px solid var(--ok-bd)}
.badge.bad{background:#f6e4de;color:var(--danger);border-color:#ecc8bd}
.empty{color:var(--faint);padding:36px;text-align:center;font-style:italic}
/* evidence tables */
.evtop{font-size:12.5px;margin-bottom:4px}
.evsec{margin:8px 0 2px;border-top:1px solid var(--hair);padding-top:6px}
.evh{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);font-weight:600;margin-bottom:3px}
.evh button.mini{float:right;text-transform:none;letter-spacing:0}
.evrow{margin:2px 0;line-height:1.5;font-size:12.5px}
.et{border-collapse:collapse;width:100%;font-size:12px}
.et th{text-align:left;color:var(--faint);font-weight:500;border-bottom:1px solid var(--line);padding:2px 8px 2px 0;white-space:nowrap}
.et td{padding:2px 8px 2px 0;vertical-align:top;border-bottom:1px solid var(--hair)}
.et tr.obs td{color:var(--un-dot)}
.et tr.axisrow td{border-top:1px solid var(--line);color:var(--link)}
.et .orh td{background:var(--hair);font-weight:600;font-family:var(--mono);font-size:11px}
.dir.up{color:var(--ok);white-space:nowrap}.dir.down{color:var(--link);white-space:nowrap}
.otherbox{margin-top:4px}
.subtree{margin-top:5px;font-size:12px;max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:7px;padding:7px;background:#fff}
.stn-node{padding:1px 2px;border-radius:3px}
.stn-kids{margin-left:12px;border-left:1px solid var(--line);padding-left:8px}
.stn-tree{font-family:var(--mono);color:var(--faint);font-size:10.5px;margin-right:4px}
.stn-node.hl{background:var(--ok-bg);font-weight:600}
.stn-node.ax{color:var(--link)}
.stylist{max-height:320px;overflow:auto}
.styrow{border:1px solid var(--line);border-radius:7px;padding:6px 9px;margin-bottom:6px;font-size:12.5px;background:var(--card)}
.styrow.acc{border-color:var(--ok-bd);background:#f2f8f3}
.styrow button{float:right;margin-left:6px}
.stytree{font-family:var(--mono);color:var(--faint);margin-right:6px}
.axtree{margin-top:5px;padding-top:5px;border-top:1px dashed var(--line)}
.mini2{font-size:11px;color:var(--faint);margin-bottom:3px}.mini2 a{color:var(--link)}
.vocab{display:inline-block;background:var(--link-bg);color:var(--link);border:1px solid #cfdce8;border-radius:4px;padding:0 4px;margin:1px;font-size:11px}
</style></head><body>
<div id="rail"></div>
<div id="main"><div id="head"></div><div id="content"><div class="empty">Loading workspace…</div></div></div>
<script>
let STATE=null,SEMTYPES=null,SEL=null,AXB=null;
let ROUTE={view:'home'};
let OPEN={};          // conditional-group open/closed, keyed by activation
let FILTER={dim:null,status:'all',text:''};
const $=s=>document.querySelector(s);
const esc=s=>(s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
// for user-controlled strings interpolated into single-quoted JS inside onclick attributes
const jsq=s=>esc(String(s==null?'':s).replace(/\\/g,'\\\\').replace(/'/g,"\\'"));
function msg(t){const el=$('#msg');if(el)el.textContent=t||'';}
const IC={
 logo:'<svg width="26" height="26" viewBox="0 0 26 26" fill="none"><circle cx="13" cy="13" r="11.5" stroke="#155e68" stroke-width="1.6"/><path d="M13 5v16M6 9.5l14 7M6 16.5l14-7" stroke="#155e68" stroke-width="1.6" stroke-linecap="round"/></svg>',
 warn:'<svg class="warnsvg" width="13" height="13" viewBox="0 0 14 14" fill="none"><path d="M7 2 12.6 11.5H1.4L7 2Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M7 6v2.6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
 right:'<svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M3 1.5 7 5 3 8.5" stroke="#8a8474" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 down:'<svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M1.5 3 5 7 8.5 3" stroke="#8a8474" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
 plus:'<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1.5v9M1.5 6h9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>'};
async function loadState(){const r=await fetch('/api/state');STATE=await r.json();
  if(!r.ok||STATE.error){$('#head').innerHTML='';
    $('#content').innerHTML='<div class="card" style="border-color:#ecc8bd"><h3 style="color:var(--danger)">Workspace error</h3>'+
      '<div style="font-size:13px">'+esc(STATE.error||('HTTP '+r.status))+'</div>'+
      '<div class="mini" style="margin-top:5px">Fix the workspace files (often dimensions_inventory.yaml) and reload.</div></div>';return;}
  render();}
/* ---------- derived data ---------- */
function dimList(){const out=[];
  (STATE.entries||[]).forEach(e=>{
    if(e.kind!=='axis')return;
    const vals=STATE.entries.filter(x=>x.dimension===e.dimension&&x.kind!=='axis');
    out.push({e,dim:e.dimension,tier:e.tier||'core',activation:e.activation||null,
      tui:e.sty_tui,styName:e.sty_name,styTree:e.sty_tree,
      total:vals.length,
      mapped:vals.filter(v=>v.status==='mapped').length,
      review:vals.filter(v=>v.status==='review').length,
      unmapped:vals.filter(v=>v.status==='unmapped').length});});
  return out;}   // server already ordered by tier/order
function grouped(){const g={core:[],cond:[],candidate:[]},bykey={};
  dimList().forEach(d=>{
    if(d.tier==='conditional'){const k=d.activation||'(no activation recorded)';
      let grp=bykey[k];if(!grp){grp=bykey[k]={act:k,dims:[]};g.cond.push(grp);}grp.dims.push(d);}
    else if(d.tier==='candidate')g.candidate.push(d);
    else g.core.push(d);});
  return g;}
function activeDim(){if(ROUTE.view==='dim')return ROUTE.dim;
  if(ROUTE.view==='value'&&SEL)return SEL.dimension;return null;}
function dotFor(d){if(d.total===0)return d.tui?'none':'none';
  if(d.mapped===d.total)return 'mapped';if(d.mapped||d.review)return 'part';return 'none';}
/* ---------- navigation ---------- */
function gotoHome(){ROUTE={view:'home'};SEL=null;render();}
function gotoDim(dim){if(FILTER.dim!==dim)FILTER={dim,status:'all',text:''};
  ROUTE={view:'dim',dim};SEL=null;AXB=null;render();}
function gotoValue(key){const e=STATE.entries.find(x=>x.key===key);if(!e)return;
  SEL=e;ROUTE={view:'value',key};render();}
function newAxis(){ROUTE={view:'dim',dim:null,isnew:true};SEL=null;
  AXB={dimension:'',query:'',note:'',tui:null,isnew:true,tier:'core',activation:''};render();}
/* ---------- rail ---------- */
function railItem(d,kid){const act=activeDim()===d.dim;
  const frac=d.total?`${d.mapped}/${d.total}`:(d.tui?'typed':'axis only');
  return `<div class="nitem ${act?'active':''} ${kid?'gkid':''}" onclick="gotoDim('${jsq(d.dim)}')">`+
    `<span class="dot ${dotFor(d)}"></span><span class="nm">${esc(d.dim)}</span>`+
    (d.tier==='core'&&d.activation?`<span class="condchip">cond.</span>`:'')+
    (!d.tui?IC.warn:'')+
    `<span class="fr">${frac}</span></div>`;}
function renderRail(){const g=grouped();const box=$('#rail');
  let h=`<div id="brand" onclick="gotoHome()">${IC.logo}<div><div class="nm">GEM Mapping Studio</div>`+
    `<div class="ws">${esc(shortWs())} · ${(STATE.counts||{}).total||0} values</div></div></div><div id="nav">`;
  h+=`<div class="tierhdr">CORE</div>`;
  h+=g.core.map(d=>railItem(d)).join('')||'<div class="navempty">none yet</div>';
  h+=`<div class="tierhdr">CONDITIONAL</div>`;
  if(!g.cond.length)h+='<div class="navempty">none yet</div>';
  g.cond.forEach(grp=>{const open=OPEN[grp.act]!==undefined?OPEN[grp.act]:grp.dims.some(d=>d.dim===activeDim());
    h+=`<div class="ghdr" onclick="toggleGroup('${jsq(grp.act)}')">${open?IC.down:IC.right}`+
       `<span>${esc(grp.act)}</span><span class="cnt">${grp.dims.length}</span></div>`;
    if(open)h+=grp.dims.map(d=>railItem(d,true)).join('');});
  h+=`<div class="tierhdr">CANDIDATE</div>`;
  h+=g.candidate.map(d=>railItem(d)).join('')||'<div class="navempty">None — promoted candidates appear here.</div>';
  h+=`</div><div id="railfoot"><button onclick="newAxis()">${IC.plus} New dimension</button></div>`;
  box.innerHTML=h;}
function toggleGroup(act){const g=grouped();const grp=g.cond.find(x=>x.act===act);
  const open=OPEN[act]!==undefined?OPEN[act]:(grp&&grp.dims.some(d=>d.dim===activeDim()));
  OPEN[act]=!open;renderRail();}
function shortWs(){const w=STATE.workspace||'';const parts=w.split('/');return parts.slice(-2).join('/');}
/* ---------- render dispatch ---------- */
function render(){if(!STATE)return;renderRail();
  if(ROUTE.view==='home')renderHome();
  else if(ROUTE.view==='dim')renderDim();
  else if(ROUTE.view==='value')renderValue();}
function head(crumbHTML,titleHTML,orient){$('#head').innerHTML=
  `<div class="crumb">${crumbHTML}</div><div class="titlerow">${titleHTML}</div>`+
  (orient?`<div class="orient">${orient}</div>`:'');}
/* ---------- HOME ---------- */
function renderHome(){const c=STATE.counts||{},g=grouped(),dims=dimList();
  head('WORKSPACE',
    `<span class="title-serif">Mapping workspace</span><span class="spacer"></span><span id="msg"></span>`+
    `<button onclick="rebuild()">Rebuild crosswalk</button><button class="primary" onclick="newAxis()">New dimension</button>`,
    `Define each dimension&rsquo;s <b>axis</b> as a UMLS semantic type, adjudicate its <b>values</b> to concepts, and export the crosswalk. Pick a dimension on the left to begin.`);
  const tot=c.total||0,m=c.mapped||0,r=c.review||0,u=c.unmapped||0;
  const pct=x=>tot?Math.round(100*x/tot):0;
  let h='';
  if(!dims.length){
    h+=`<div class="card"><h3>Empty workspace</h3><div style="font-size:13px">This mapping directory has no dimensions yet. `+
       `<b>New dimension</b> creates the first axis from scratch; the Semantic Network reference is built in, so no API key is needed for that.</div></div>`;
    $('#content').innerHTML=h;return;}
  h+=`<div class="card"><h3>Adjudication progress</h3>`+
     `<div class="bar"><div class="m" style="width:${pct(m)}%"></div><div class="r" style="width:${pct(r)}%"></div><div class="u" style="width:${100-pct(m)-pct(r)}%"></div></div>`+
     `<div class="legend"><span><span class="ldot" style="background:var(--ok-dot)"></span><b>${m}</b> mapped</span>`+
     `<span><span class="ldot" style="background:var(--rev-dot)"></span><b>${r}</b> in review</span>`+
     `<span><span class="ldot" style="background:var(--un-dot)"></span><b>${u}</b> unmapped</span>`+
     `<span style="margin-left:auto" class="mono mini">${tot} values · ${dims.length} dimensions · ${c.curated||0} curated</span></div></div>`;
  const needs=STATE.entries.filter(x=>x.kind!=='axis'&&(x.status==='review'||!x.curated));
  if(needs.length){h+=`<div class="card"><h3>Needs attention · ${needs.length}<span class="hint">review status or not yet curated — across all dimensions</span></h3>`+
    `<div style="max-height:240px;overflow:auto">`+needs.map(x=>
      `<div class="hrow" style="grid-template-columns:250px minmax(0,1fr) 104px" onclick="gotoValue('${jsq(x.key)}')">`+
      `<div class="dn"><span class="dot ${esc(x.status)}"></span><span>${esc(String(x.token))}</span></div>`+
      `<div class="mut" style="font-size:12px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(x.dimension)}`+
      `${x.cui?' · '+esc(x.matched_name||'')+' <span class="mini">(auto)</span>':''}</div>`+
      `<div class="st"><span class="chip st-${esc(x.status)}">${esc(x.status)}</span></div></div>`).join('')+`</div></div>`;}
  const rowHTML=d=>{const axis=d.tui?
      `<span class="chip tui">${esc(d.tui)}</span> <span>${esc(d.styName||'')}</span> <span class="stn" style="font-size:11px">${esc(d.styTree||'')}</span>`:
      `${IC.warn} <span style="color:var(--warn);font-weight:500">Axis type not set</span>`;
    const w=d.total?Math.round(100*d.mapped/d.total):0,wr=d.total?Math.round(100*d.review/d.total):0;
    const st=d.total===0?'<span class="chip st-unmapped">no values</span>':
      d.mapped===d.total?'<span class="chip st-mapped">complete</span>':
      (d.mapped||d.review)?'<span class="chip st-review">in progress</span>':'<span class="chip st-unmapped">not started</span>';
    return `<div class="hrow" onclick="gotoDim('${jsq(d.dim)}')">`+
      `<div class="dn"><span>${esc(d.dim)}</span>${d.activation&&d.tier==='core'?'<span class="condchip">cond. required</span>':''}</div>`+
      `<div style="display:flex;align-items:center;gap:6px;min-width:0;font-size:12px">${axis}</div>`+
      `<div><span class="minibar"><span style="width:${w}%;background:var(--ok-dot)"></span><span style="width:${wr}%;background:var(--rev-dot)"></span></span> `+
      `<span class="mono" style="font-size:11px;color:var(--mut)">${d.mapped}/${d.total}</span></div>`+
      `<div class="st">${st}</div></div>`;};
  h+=`<div class="card"><h3>Core dimensions<span class="hint">ordered by the model, not the alphabet</span></h3>`+
     g.core.map(rowHTML).join('')+`</div>`;
  if(g.cond.length){h+=`<div class="card"><h3>Conditional dimensions</h3>`+
    g.cond.map(grp=>`<div class="condline"><span class="act">${esc(grp.act)}</span>`+
      grp.dims.map(d=>`<a href="#" onclick="gotoDim('${jsq(d.dim)}');return false">${esc(d.dim)}</a>`+
        (d.total?` <span class="f">${d.mapped}/${d.total}</span>`:'')).join('<span class="mut"> · </span>')+
      `</div>`).join('')+`</div>`;}
  if(g.candidate.length){h+=`<div class="card"><h3>Candidate dimensions</h3>`+
    g.candidate.map(rowHTML).join('')+`</div>`;}
  h+=`<div class="card"><h3>Workspace</h3><div class="mono" style="font-size:11.5px;word-break:break-all">${esc(STATE.workspace||'')}</div>`+
     `<div class="mini" style="margin-top:5px">dimensions_inventory.yaml defines the structure (tier / order / activation live there); `+
     `umls_crosswalk.yaml holds the harness results; adjudications.yaml records your decisions.</div></div>`;
  $('#content').innerHTML=h;}
/* ---------- DIMENSION view ---------- */
function renderDim(){const isnew=!!ROUTE.isnew;
  const d=isnew?null:dimList().find(x=>x.dim===ROUTE.dim);
  if(!isnew&&!d){gotoHome();return;}
  const e=d?d.e:null;
  if(!AXB)AXB=e?{dimension:e.dimension,query:e.axis_query||'',note:e.axis_note||'',tui:e.sty_tui||null,
                 isnew:!e.in_inventory,tier:e.tier||'core',activation:e.activation||''}
              :{dimension:'',query:'',note:'',tui:null,isnew:true,tier:'core',activation:''};
  const tierchip=`<span class="chip tier">${esc((AXB.tier||'core').toUpperCase())}</span>`;
  head(`<a href="#" onclick="gotoHome();return false">WORKSPACE</a> › ${esc((AXB.dimension||'NEW').toUpperCase())}`,
    `<span class="title-mono">${esc(AXB.dimension||'new dimension')}</span>${tierchip}`+
    (AXB.activation?`<span class="mini mono">${esc(AXB.activation)}</span>`:'')+
    `<span class="spacer"></span><span id="msg"></span>`+
    `<button onclick="rebuild()">Rebuild</button>`+
    `<button class="primary" onclick="axbSave()">${AXB.isnew?'Create axis':'Save axis'}</button>`,
    isnew?'A dimension&rsquo;s axis maps it to a UMLS <b>semantic type</b>; the type&rsquo;s subtree becomes the search filter for every value of the dimension.':'');
  const ro=AXB.isnew?'':'readonly';
  let h=`<div class="card"><h3>Axis</h3><div class="axgrid">`+
    `<div class="axtype"><div id="axsel"></div></div>`+
    `<div>`+
      (AXB.isnew?`<div class="axrow"><label>dimension</label><input id="axdim" value="${esc(AXB.dimension)}" placeholder="e.g. resolution"></div>`+
        `<div class="axrow"><label>tier</label><select id="axtier">`+
          ['core','conditional','candidate'].map(t=>`<option ${AXB.tier===t?'selected':''}>${t}</option>`).join('')+`</select></div>`+
        `<div class="axrow"><label>activation</label><input id="axact" value="${esc(AXB.activation)}" placeholder="e.g. knowledge_domain: GENE_FUNCTION (conditional only)"></div>`:'')+
      `<div class="axrow"><label>query</label><input id="axq" value="${esc(AXB.query)}" placeholder="seed query, e.g. Spatial concept"><button onclick="axbRun()">Run query</button></div>`+
      `<div class="axrow"><label>note</label><input id="axnote" value="${esc(AXB.note)}" placeholder="what this axis means"></div>`+
      `<div class="mini" style="margin-left:82px">Run query surfaces the semantic <i>types</i> of matching concepts — an axis maps to a type, not a concept.</div>`+
    `</div></div>`+
    `<div id="axprev" style="margin-top:10px"></div>`+
    `<details style="margin-top:8px"><summary class="mini" style="cursor:pointer">Browse all 127 semantic types</summary>`+
    `<div class="searchbar" style="margin-top:8px"><input id="styq" placeholder="filter by name / TUI / tree…"></div>`+
    `<div id="styresults" class="stylist"></div></details></div>`;
  if(e){const vals=STATE.entries.filter(x=>x.dimension===e.dimension&&x.kind!=='axis');
    h+=`<div class="card"><h3>Values · ${vals.length}`+
      `<span class="hint">${d.mapped} mapped · ${d.review} in review · ${d.unmapped} unmapped</span></h3>`+
      `<div style="display:flex;gap:8px;margin-bottom:6px">`+
      `<select id="fstatus" onchange="setFilter()" style="font-size:12px">`+
        `<option value="all">All</option><option value="needs">Needs attention</option><option value="mapped">Mapped</option>`+
        `<option value="unmapped">Unmapped</option><option value="curated">Curated</option><option value="auto">Auto (not curated)</option></select>`+
      `<input id="ftext" oninput="setFilter()" placeholder="filter token…" style="width:180px;font-size:12px">`+
      `</div><div id="vtbox">${valuesTable(vals)}</div></div>`;
    if(!vals.length)h+=`<div class="mini" style="margin:-6px 0 12px 4px">No values in the crosswalk yet — values come from the inventory/schema; <b>Rebuild</b> generates and resolves them.</div>`;}
  $('#content').innerHTML=h;
  if(AXB.isnew){['axdim','axtier','axact'].forEach(id=>{const el=$('#'+id);if(el)el.addEventListener('input',()=>{
      AXB.dimension=($('#axdim')||{}).value||'';AXB.tier=($('#axtier')||{}).value||'core';AXB.activation=($('#axact')||{}).value||'';});});
    const t=$('#axtier');if(t)t.addEventListener('change',()=>{AXB.tier=t.value;});}
  ['axq','axnote'].forEach(id=>{const el=$('#'+id);if(el)el.addEventListener('input',()=>{
      AXB.query=($('#axq')||{}).value||'';AXB.note=($('#axnote')||{}).value||'';});});
  const q=$('#axq');if(q)q.addEventListener('keydown',ev=>{if(ev.key==='Enter')axbRun();});
  const sq=$('#styq');if(sq)sq.addEventListener('input',axbPicker);
  const fs=$('#fstatus');if(fs)fs.value=FILTER.status;const ft=$('#ftext');if(ft)ft.value=FILTER.text;
  loadSemTypes().then(()=>{axbPicker();axbRenderSel();});}
function setFilter(){FILTER.dim=ROUTE.dim;FILTER.status=($('#fstatus')||{}).value||'all';FILTER.text=($('#ftext')||{}).value||'';
  const e=dimList().find(x=>x.dim===ROUTE.dim);if(!e)return;
  const vals=STATE.entries.filter(x=>x.dimension===ROUTE.dim&&x.kind!=='axis');
  $('#vtbox').innerHTML=valuesTable(vals);}
function passFilter(e){const f=FILTER.status,t=FILTER.text.toLowerCase();
  if(t&&!(String(e.token||'')+' '+e.dimension).toLowerCase().includes(t))return false;
  if(f==='all')return true;if(f==='mapped')return e.status==='mapped';if(f==='unmapped')return e.status==='unmapped';
  if(f==='curated')return e.curated;if(f==='auto')return e.status==='mapped'&&!e.curated;
  if(f==='needs')return e.status==='review'||!e.curated;return true;}
function valuesTable(vals){const rows=vals.filter(passFilter).map(e=>{
    const map=e.cui?`<span>${esc(e.matched_name||'')}</span> <span class="cui">${esc(e.cui)}</span>`+
      (e.root_source?` <span class="sab">${esc(e.root_source)}</span>`:''):'<span class="mut">—</span>';
    return `<tr class="vrow" onclick="gotoValue('${jsq(e.key)}')">`+
      `<td style="width:16px"><span class="dot ${esc(e.status)}" style="display:inline-block"></span></td>`+
      `<td class="tk">${esc(e.token)}${e.kind!=='value'?` <span class="condchip">${esc(e.kind)}</span>`:''}</td>`+
      `<td class="mut">${esc(e.query)}</td><td>${map}</td>`+
      `<td style="text-align:right"><span class="chip st-${esc(e.status)}">${esc(e.status)}</span>`+
      (e.curated?' <span class="badge">curated</span>':'')+`</td></tr>`;}).join('');
  return rows?`<table class="vt"><tr><th></th><th>TOKEN</th><th>QUERY</th><th>MAPPING</th><th style="text-align:right">STATUS</th></tr>${rows}</table>`
    :'<div class="mini" style="padding:8px 0">no values match the filter</div>';}
/* ---------- axis builder internals ---------- */
async function axbRun(){const q=(($('#axq')||{}).value||'').trim();const box=$('#axprev');if(!box)return;
  if(!q){box.innerHTML='<span class="mini">enter a query first</span>';return;}
  box.innerHTML='<span class="mini">searching UMLS…</span>';
  const j=await (await fetch('/api/search?string='+encodeURIComponent(q))).json();
  if(j.error){box.innerHTML='<span style="color:var(--danger)">'+esc(j.error)+'</span>';return;}
  const res=(j.results||[]).slice(0,60);
  if(!res.length){box.innerHTML='<span class="mini">no results — offline (no key), or no match. You can still pick a type below.</span>';return;}
  const norm=s=>(s||'').toLowerCase(),byT={};
  res.forEach(c=>(c.semantic_types||[]).forEach(nm=>{
    const t=(SEMTYPES||[]).find(x=>norm(x.name)===norm(nm));if(!t)return;
    const g=byT[t.tui]||(byT[t.tui]={tui:t.tui,name:t.name,tree:t.tree,n:0,ex:[]});
    g.n++;if(g.ex.length<5)g.ex.push(c.name);}));
  const types=Object.values(byT).sort((a,b)=>b.n-a.n);
  if(!types.length){box.innerHTML='<span class="mini">'+res.length+' concepts matched but none carried a recognised semantic type. Pick a type below.</span>';return;}
  const rows=types.map(t=>`<div class="styrow ${t.tui===AXB.tui?'acc':''}"><span class="stytree">${esc(t.tree)}</span> ${esc(t.name)} <span class="cui">${esc(t.tui)}</span> <span class="mut">&times;${t.n}</span>`+
    `<button class="ok mini" onclick="axbSet('${t.tui}')">${t.tui===AXB.tui?'✓ axis type':'use as axis type'}</button>`+
    `<button class="mini" onclick="stnToggle(this,'${t.tui}')">tree</button>`+
    `<div class="mini">e.g. ${esc(t.ex.join(', '))}</div></div>`).join('');
  box.innerHTML=`<div class="mini" style="margin-bottom:5px">${types.length} semantic type${types.length===1?'':'s'} across ${res.length} matching concepts — click one to set the axis type:</div><div class="stylist">${rows}</div>`;}
function axbRenderSel(){const box=$('#axsel');if(!box)return;const t=(SEMTYPES||[]).find(x=>x.tui===AXB.tui);
  if(!t){box.innerHTML=`<div style="display:flex;align-items:center;gap:7px">${IC.warn}<span style="color:var(--warn);font-weight:500">Axis type not set</span></div>`+
    `<div class="mini" style="margin-top:5px">Run the query or browse the types to choose one — value searches are unconstrained until then.</div>`;return;}
  const sub=(SEMTYPES||[]).filter(x=>x.tree===t.tree||x.tree.startsWith(t.tree+'.'));
  box.innerHTML=`<span class="tnm">${esc(t.name)}</span> <span class="chip tui">${esc(t.tui)}</span> <span class="stn" style="font-size:11.5px">${esc(t.tree)}</span>`+
    `<div class="mini" style="margin-top:4px">value searches constrained to <b>${sub.length}</b> semantic type${sub.length===1?'':'s'} (the axis subtree)</div>`+
    (t.definition?`<div class="def show" style="margin-top:7px">${esc(t.definition)}</div>`:'')+
    `<div class="subtree" style="margin-top:8px">${stnPlaceHTML(t.tui)}</div>`;}
function axbPicker(){const box=$('#styresults');if(!box)return;const q=(($('#styq')||{}).value||'').toLowerCase();
  box.innerHTML=(SEMTYPES||[]).filter(t=>!q||(t.name+' '+t.tui+' '+t.tree).toLowerCase().includes(q)).slice(0,80).map(t=>
    `<div class="styrow ${t.tui===AXB.tui?'acc':''}"><span class="stytree">${esc(t.tree)}</span> ${esc(t.name)} <span class="cui">${esc(t.tui)}</span>`+
    `<button class="ok mini" onclick="axbSet('${t.tui}')">${t.tui===AXB.tui?'✓ chosen':'choose'}</button>`+
    `<button class="mini" onclick="stnToggle(this,'${t.tui}')">tree</button>`+
    (t.definition?`<div class="def show">${esc(t.definition)}</div>`:'')+`</div>`).join('');}
function axbSet(tui){AXB.tui=tui;axbRenderSel();axbPicker();}
function stnPlaceHTML(tui){const t=(SEMTYPES||[]).find(x=>x.tui===tui);if(!t)return '<i>type not found</i>';
  const dep=s=>s.split('.').length;
  const node=(n,inner)=>`<div class="stn-node${n.tui===tui?' hl':''}"><span class="stn-tree">${esc(n.tree)}</span> `+
    `<a href="#" onclick="axbSet('${n.tui}');return false">${esc(n.name)}</a> <span class="cui">${esc(n.tui)}</span>`+
    (inner?`<div class="stn-kids">${inner}</div>`:'')+`</div>`;
  const kidsOf=n=>(SEMTYPES||[]).filter(x=>x.tree.startsWith(n.tree+'.')&&dep(x.tree)===dep(n.tree)+1)
                                .sort((a,b)=>a.tree<b.tree?-1:1);
  const sub=n=>node(n,kidsOf(n).map(sub).join(''));
  const segs=t.tree.split('.'),chain=[];
  for(let i=1;i<segs.length;i++){const a=(SEMTYPES||[]).find(x=>x.tree===segs.slice(0,i).join('.'));if(a)chain.push(a);}
  const parent=chain.length?chain[chain.length-1]:null;
  let core;
  if(parent){core=node(parent,kidsOf(parent).map(s=>s.tui===t.tui?sub(t):node(s,'')).join(''));
    for(let i=chain.length-2;i>=0;i--)core=node(chain[i],core);}
  else core=sub(t);
  return `<div class="stn-tree">${core}</div>`;}
function stnToggle(btn,tui){const row=btn.closest('.styrow')||btn.parentElement;
  const box=row.querySelector(':scope > .axtree');
  if(box){box.remove();return;}
  const d=document.createElement('div');d.className='axtree';d.innerHTML=stnPlaceHTML(tui);row.appendChild(d);}
async function axbSave(){if(!AXB)return;
  AXB.query=($('#axq')||{}).value??AXB.query;AXB.note=($('#axnote')||{}).value??AXB.note;
  if(AXB.isnew){AXB.dimension=($('#axdim')||{}).value||AXB.dimension;
    AXB.tier=($('#axtier')||{}).value||AXB.tier;AXB.activation=($('#axact')||{}).value??AXB.activation;}
  if(!AXB.dimension.trim()){msg('dimension name required');return;}
  msg('saving axis…');
  const body={dimension:AXB.dimension,semantic_type:AXB.tui||'',query:AXB.query,note:AXB.note};
  if(AXB.isnew){body.tier=AXB.tier;if(AXB.activation)body.activation=AXB.activation;}
  const j=await (await fetch('/api/axis',{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify(body)})).json();
  if(j.error){msg('error: '+j.error);return;}
  const dim=AXB.dimension.trim();
  ROUTE={view:'dim',dim};AXB=null;   // route first: loadState() renders with it
  await loadState();
  msg('saved axis '+dim+' — Rebuild to (re)generate value candidates');}
/* ---------- VALUE view ---------- */
function renderValue(){SEL=STATE.entries.find(x=>x.key===ROUTE.key)||SEL;
  if(!SEL){gotoHome();return;}const e=SEL;
  head(`<a href="#" onclick="gotoHome();return false">WORKSPACE</a> › `+
       `<a href="#" onclick="gotoDim('${jsq(e.dimension)}');return false">${esc(e.dimension.toUpperCase())}</a> › ${esc(String(e.token))}`,
    `<span class="title-mono">${esc(String(e.token))}</span>`+
    `<span class="mini">value of <span class="mono">${esc(e.dimension)}</span>${e.kind!=='value'?' · '+esc(e.kind):''}</span>`+
    `<span class="chip st-${esc(e.status)}">${esc(e.status)}</span>`+(e.curated?' <span class="badge">curated</span>':'')+
    `<span class="spacer"></span><span id="msg"></span><button onclick="rebuild()">Rebuild</button>`,'');
  const cur=e.status==='mapped'?`<span class="now">mapped &rarr; <b>${esc(e.matched_name)}</b> <span class="cui">${esc(e.cui)}</span>`+
      (e.curated?` <span class="badge">${e.fetched?'curated · fetched':'curated'}</span>`:' <span class="mini">(auto)</span>')+`</span>`:
    e.status==='unmapped'?`<span class="now">unmapped${e.curated?' <span class="badge">curator</span>':''}</span>`:
    `<span class="now">review</span>`;
  const filt=e.dim_sty_tui?`<span class="chip tui">&sub; axis type ${esc(e.dim_sty_tui)} subtree</span>`
    :`<span class="chip warnc">${IC.warn} axis untyped — search unconstrained</span>`;
  $('#content').innerHTML=`
   <div class="card"><h3>GEM meaning</h3><div style="font-size:13.5px">${esc(e.meaning)||'<span class="mini">(no gloss)</span>'}</div>
     <div class="mini" style="margin-top:4px">query used: <b>${esc(e.query)}</b></div></div>
   <div class="card"><h3>Decision</h3>${cur}${e.error?` <span style="color:var(--danger)">${esc(e.error)}</span>`:''}
     <div class="curbar">
       <button class="warn" onclick="decide('unmapped')">No faithful concept</button>
       <button onclick="decide('clear')">Clear decision</button>
       ${e.note?`<span class="mini">note: ${esc(e.note)}</span>`:''}
     </div>
     <textarea id="note" placeholder="optional note / rationale">${esc(e.note||'')}</textarea>
   </div>
   <div class="card"><h3>Query candidates · ${e.candidates.length}</h3>${e.candidates.map(c=>candHTML(c)).join('')||'<span class="mini">none returned by the harness query</span>'}</div>
   <div class="card"><h3>Search the Metathesaurus <span style="margin-left:6px">${filt}</span></h3>
     <div class="searchbar"><input id="sq" placeholder="concept term…" value="${esc(e.token?String(e.token).replace(/_/g,' ').toLowerCase():e.query)}">
       <select id="ssab"><option value="">all sources</option><option>MSH</option><option>NCI</option><option>SNOMEDCT_US</option><option>GO</option><option>HPO</option></select>
       <button class="primary" onclick="runSearch()">Search</button></div>
     <div id="sresults"></div></div>`;
  $('#sq').addEventListener('keydown',ev=>{if(ev.key==='Enter')runSearch();});}
function candHTML(c){const acc=SEL&&SEL.decision_cui===c.cui;
  return `<div class="cand ${acc?'acc':''}"><div class="row"><span class="n">${esc(c.name)} <span class="cui">${esc(c.cui)}</span></span>`+
    `<button class="mini" onclick="loadDef('${c.cui}',this)">evidence</button>`+
    `<button class="ok" onclick="decide('accept','${c.cui}')">${acc?'✓ accepted':'accept'}</button></div>`+
    `<div class="sty">${esc((c.sty||c.semantic_types||[]).join(', '))}${c.src||c.root_source?' · '+esc(c.src||c.root_source):''}</div>`+
    `<div class="def"></div></div>`;}
let _semReq=null;
async function loadSemTypes(){if(SEMTYPES)return SEMTYPES;
  if(!_semReq)_semReq=fetch('/api/semantictypes').then(r=>r.json()).then(j=>{SEMTYPES=j.types;return SEMTYPES;});
  return _semReq;}
async function loadDef(cui,btn){const box=btn.closest('.cand').querySelector('.def');
  if(box.classList.contains('show')){box.classList.remove('show');return;}
  box.innerHTML='loading concept evidence…';box.classList.add('show');
  const axis=SEL&&SEL.dim_sty_tui?('&axis='+SEL.dim_sty_tui):'';
  const j=await (await fetch('/api/concept?cui='+cui+axis)).json();
  await loadSemTypes();
  renderInfo(box,cui,j.evidence||{},j.definitions||[]);}
function renderInfo(box,cui,e,defs){
  if(e.error){box.innerHTML='<i>'+esc(e.error)+'</i>';return;}
  const spec=(e.sty_path&&e.sty_path[0])||{},axis=e.axis_sty;
  const pathRows=(e.sty_path||[]).map((p,i)=>`<tr><td>${i?'<span class="mut">&uarr;</span>':'<b>STY</b>'}</td><td>${esc(p.name)}</td><td class="cui">${esc(p.tui)}</td><td class="stn">${esc(p.tree)}</td></tr>`).join('');
  const axbadge=axis?(e.under_axis?' <span class="badge">in axis branch</span>':' <span class="badge bad">outside axis branch</span>'):'';
  const styBlock=`<div class="evsec"><div class="evh">Semantic type${axbadge}<button class="mini" onclick="toggleSubtree(this,'${esc(spec.tui||'')}','${axis?esc(axis.tui):''}')">subtree</button></div>`+
    `<table class="et"><tr><th></th><th>STY</th><th>TUI</th><th>STN</th></tr>${pathRows}`+
    (axis?`<tr class="axisrow"><td><b>axis</b></td><td>${esc(axis.name)}</td><td class="cui">${esc(axis.tui)}</td><td class="stn">${esc(axis.stn)}</td></tr>`:'')+
    `</table><div class="subtree" style="display:none"></div></div>`;
  const vrows=(e.atom_rows||[]).map(a=>`<tr class="${a.obsolete?'obs':''}"><td>${esc(a.sab)}</td><td>${esc(a.str)}</td><td>${esc(a.tty)}</td><td class="cui">${esc(a.code)}</td></tr>`).join('');
  const vocBlock=`<div class="evsec"><div class="evh">Vocabularies (${(e.sabs||[]).length} sources, English)</div><table class="et"><tr><th>SAB</th><th>STR</th><th>TTY</th><th>Code</th></tr>${vrows||'<tr><td colspan=4><i>none</i></td></tr>'}</table></div>`;
  const rid=r=>esc(r.cui||r.code||'');
  const rrows=(e.relations||[]).map(r=>`<tr><td class="dir ${r.dir}">${r.dir==='up'?'&uarr; is_a':'&darr; is_a'}</td><td>${esc(r.name)}</td><td class="cui">${rid(r)}</td><td>${esc((r.sabs||[]).join(', '))}</td></tr>`).join('');
  const relBlock=`<div class="evsec"><div class="evh">Hierarchy (is_a)</div><table class="et"><tr><th>dir</th><th>concept</th><th>id</th><th>sources</th></tr>${rrows||'<tr><td colspan=4><i>no is_a parents or children in English vocabularies</i></td></tr>'}</table></div>`;
  const org=(e.other_relations||[]);
  const orInner=org.map(g=>{
    const items=g.items.map(it=>`<tr><td>${esc(it.name)}</td><td class="cui">${rid(it)}</td><td>${esc((it.sabs||[]).join(', '))}</td></tr>`).join('');
    const more=g.n>g.items.length?`<tr><td colspan=3 class="mut">+${g.n-g.items.length} more</td></tr>`:'';
    return `<tr class="orh"><td colspan=3>${esc(g.rela)} <span class="mut">(${g.n})</span></td></tr>${items}${more}`;}).join('');
  const otherBlock=org.length?`<div class="evsec"><div class="evh">Other relations<button class="mini" data-k="${org.length}" onclick="toggleOther(this)">show ${org.length} kinds</button></div><div class="otherbox" style="display:none"><table class="et"><tr><th>concept</th><th>id</th><th>sources</th></tr>${orInner}</table></div></div>`:'';
  const df=(defs||[]).map(d=>`<b>[${esc(d.source)}]</b> ${esc(d.value)}`).join('<br>')||'<i>no definition</i>';
  const rollBlock=`<div class="evsec"><div class="evh">Rollup<button class="mini" onclick="loadRollup(this.closest('.evsec').querySelector('.rollbox'),'${cui}')">roll up &darr;</button></div><div class="rollbox"></div></div>`;
  box.innerHTML=`<div class="evtop"><b>${esc(e.name)}</b> <span class="cui">${esc(cui)}</span> &middot; status ${esc(e.status||'?')} &middot; ${e.atom_count||0} atoms</div>`+
    styBlock+vocBlock+relBlock+otherBlock+
    `<div class="evsec"><div class="evh">Definition</div><div class="evrow">${df}</div></div>`+rollBlock;}
function toggleOther(btn){const box=btn.closest('.evsec').querySelector('.otherbox');const show=box.style.display==='none';box.style.display=show?'block':'none';btn.textContent=(show?'hide ':'show ')+btn.dataset.k+' kinds';}
function toggleSubtree(btn,specTui,axisTui){const box=btn.closest('.evsec').querySelector('.subtree');
  if(box.style.display!=='none'){box.style.display='none';return;}
  box.style.display='block';
  const root=axisTui||specTui,rt=(SEMTYPES||[]).find(t=>t.tui===root);
  if(!rt){box.innerHTML='<i>semantic type not found</i>';return;}
  const inSub=(SEMTYPES||[]).filter(t=>t.tree===rt.tree||t.tree.startsWith(rt.tree+'.'));
  const dep=s=>s.split('.').length;
  const render2=n=>{const kids=inSub.filter(t=>t.tree.startsWith(n.tree+'.')&&dep(t.tree)===dep(n.tree)+1);
    const hl=n.tui===specTui?' hl':(n.tui===axisTui?' ax':'');
    return `<div class="stn-node${hl}"><span class="stn-tree">${esc(n.tree)}</span> ${esc(n.name)} <span class="cui">${esc(n.tui)}</span>`+
      (kids.length?`<div class="stn-kids">${kids.map(render2).join('')}</div>`:'')+`</div>`;};
  box.innerHTML=render2(rt);}
async function loadRollup(box,cui,sab){box.innerHTML='rolling up is_a ancestors…';
  const j=await (await fetch('/api/rollup?cui='+cui+(sab?'&use_sab='+encodeURIComponent(sab):''))).json();
  const rows=(j.rollup||[]).map(a=>`<tr><td>${esc(a.name)}</td><td class="cui">${esc(a.code)}</td><td>${esc(a.sab)}</td></tr>`).join('');
  const opts=j.sabs||[];
  const nav=opts.length?`<div class="mini2">vocabulary: <a href="#" data-cui="${cui}" onclick="rollNav(this,'');return false">auto</a>${opts.map(s=>` &middot; <a href="#" data-cui="${cui}" onclick="rollNav(this,'${esc(s)}');return false">${esc(s)}</a>`).join('')}${sab?' &mdash; <b>'+esc(sab)+'</b>':''}</div>`:'';
  box.innerHTML=nav+`<table class="et"><tr><th>is_a ancestor</th><th>code</th><th>vocab</th></tr>${rows||'<tr><td colspan=3><i>no is_a ancestors in English vocabularies</i></td></tr>'}</table>`;}
function rollNav(a,sab){loadRollup(a.closest('.rollbox'),a.dataset.cui,sab||null);}
async function runSearch(){const q=$('#sq').value,sab=$('#ssab').value;const box=$('#sresults');box.innerHTML='<span class="mini">searching…</span>';
  const stys=SEL.dim_sty_filter||'';
  const url='/api/search?string='+encodeURIComponent(q)+(sab?'&sabs='+sab:'')+(stys?'&stys='+encodeURIComponent(stys):'');
  const r=await fetch(url);const j=await r.json();
  if(j.error){box.innerHTML='<span style="color:var(--danger)">'+esc(j.error)+'</span>';return;}
  box.innerHTML=(j.results||[]).slice(0,15).map(c=>candHTML(c)).join('')||'<span class="mini">no results (within the axis type)</span>';}
async function decide(verdict,cui){const note=($('#note')||{}).value||'';
  const body={key:SEL.key,verdict};if(cui)body.cui=cui;if(note)body.note=note;
  msg('saving…');const r=await fetch('/api/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json();if(j.error){msg('error: '+j.error);return;}
  await loadState();msg('saved '+SEL.key+' ('+verdict+') — Rebuild to refresh status');}
async function rebuild(){msg('rebuilding (querying UMLS)…');const r=await fetch('/api/rebuild',{method:'POST'});const j=await r.json();
  if(j.error){msg('error: '+j.error);return;}await loadState();msg('rebuilt: '+JSON.stringify(j.counts));}
loadState();
</script></body></html>'''


def main(argv=None):
    global client
    import argparse
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(
        prog="gem-umls-adjudicate",
        description="Local UMLS crosswalk adjudication + axis builder. Point it "
                    "at a mapping directory (--data-dir); an empty one lets you "
                    "construct axes from scratch, a populated one lets you modify.")
    ap.add_argument("--data-dir", help="mapping workspace directory (inventory / "
                    "crosswalk / adjudications). May be empty. Defaults to the "
                    "repo's data/umls, or $GEM_DATA_DIR.")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = ap.parse_args(argv)

    # Point every path (this module AND the harness) at the chosen workspace by
    # setting GEM_DATA_DIR and re-execing once -- path constants resolve at import,
    # so an in-process override would not reach already-imported modules.
    if args.data_dir:
        want = str(Path(args.data_dir).expanduser().resolve())
        if os.environ.get("GEM_DATA_DIR") != want:
            os.environ["GEM_DATA_DIR"] = want
            os.execv(sys.executable,
                     [sys.executable, "-m", "forome.gem.umls.adjudicate_ui", *argv])

    key = api_key()
    if key:
        client = UTSClient(key, cache_dir=H.CACHE_DIR)
    else:
        # Axis construction needs only the Semantic Network (reference data), so
        # run without a key -- value search/concept info are simply inert.
        print("WARNING: no UMLS_API_KEY found; running offline (axis construction "
              "works; live value search/concept info are disabled).")
        client = NullClient()

    if not H.INVENTORY.is_file() and not CROSSWALK.is_file():
        print(f"Workspace {DATA_DIR} has no inventory or crosswalk yet -- "
              f"starting empty; use “New axis” to build one from scratch.")

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"GEM Mapping Studio running at {url}  (workspace: {DATA_DIR})  (Ctrl-C to stop)")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
