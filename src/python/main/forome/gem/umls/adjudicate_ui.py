#!/usr/bin/env python3
"""Local, Metathesaurus-integrated adjudication UI + axis builder for the UMLS
crosswalk.

A small localhost web app with two jobs, over one mapping directory (the
"workspace"):

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

    entries = []
    for dim in sorted(set(dims) | set(values_by_dim)):
        axis = (dims.get(dim) or {}).get("axis") or {}
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


def save_axis(dimension: str, semantic_type=None, query=None, note=None) -> dict:
    """Create or update a dimension's axis block in the workspace inventory,
    creating the inventory file (and directory) if absent. This is how a new
    axis is constructed from scratch and how an existing one is modified.
    Returns the resulting axis block."""
    dimension = (dimension or "").strip()
    if not dimension:
        raise ValueError("a dimension name is required")
    if semantic_type and not stylib.get(semantic_type):
        raise ValueError(f"unknown semantic type {semantic_type!r}")
    inv = yaml.safe_load(H.INVENTORY.read_text()) if H.INVENTORY.is_file() else {}
    inv = inv or {}
    block = inv.setdefault("dimensions", {}).setdefault(dimension, {})
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
                axis = save_axis(data.get("dimension"),
                                 semantic_type=data.get("semantic_type") or None,
                                 query=data.get("query"), note=data.get("note"))
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
<title>GEM &rarr; UMLS adjudication</title>
<style>
:root{--bg:#f7f8fa;--panel:#fff;--line:#e2e5ea;--ink:#1c2330;--mut:#6b7280;
--green:#0a8a4a;--amber:#b7791f;--grey:#9aa1ac;--blue:#2456c9;}
*{box-sizing:border-box}body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
#top{display:flex;align-items:center;gap:14px;padding:8px 14px;background:var(--panel);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
#top h1{font-size:15px;margin:0;font-weight:600}
.counts span{display:inline-block;margin-right:10px;font-size:12px;color:var(--mut)}
.counts b{color:var(--ink)}
button{font:inherit;padding:5px 10px;border:1px solid var(--line);background:#fff;border-radius:6px;cursor:pointer}
button:hover{background:#f0f2f5}button.primary{background:var(--blue);color:#fff;border-color:var(--blue)}
button.ok{background:var(--green);color:#fff;border-color:var(--green)}
button.warn{background:#fff;color:var(--amber);border-color:var(--amber)}
#msg{font-size:12px;color:var(--mut);margin-left:auto}
#wrap{display:flex;height:calc(100vh - 45px)}
#list{width:340px;overflow:auto;border-right:1px solid var(--line);background:var(--panel)}
#filter{padding:8px;position:sticky;top:0;background:var(--panel);border-bottom:1px solid var(--line)}
#filter select,#filter input{font:inherit;padding:4px 6px;border:1px solid var(--line);border-radius:5px}
#filter input{width:130px}
.dimhdr{padding:6px 10px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);background:#eef0f3;position:sticky;top:41px}
.item{padding:6px 10px;border-bottom:1px solid var(--line);cursor:pointer;display:flex;gap:8px;align-items:baseline}
.item:hover{background:#f0f4ff}.item.sel{background:#e3ebff}
.dot{width:8px;height:8px;border-radius:50%;flex:0 0 8px;margin-top:5px}
.dot.mapped{background:var(--green)}.dot.unmapped{background:var(--grey)}.dot.review{background:var(--amber)}
.tk{font-weight:500}.mini{font-size:11px;color:var(--mut)}
.badge{font-size:10px;padding:1px 5px;border-radius:8px;background:#eaf6ef;color:var(--green);border:1px solid #bfe6cf}
#detail{flex:1;overflow:auto;padding:16px 20px}
#detail h2{font-size:16px;margin:0 0 2px}.sub{color:var(--mut);font-size:12px;margin-bottom:12px}
.card{border:1px solid var(--line);border-radius:8px;background:var(--panel);padding:12px;margin-bottom:12px}
.card h3{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:var(--mut)}
.mean{font-size:14px}
.cand{border:1px solid var(--line);border-radius:7px;padding:8px 10px;margin-bottom:7px}
.cand .n{font-weight:500}.cand.acc{border-color:var(--green);background:#f4fbf6}
.sty{font-size:11px;color:var(--mut)}
.cand .row{display:flex;align-items:center;gap:8px}.cand .row .n{flex:1}
.def{margin-top:6px;font-size:12.5px;color:#334;background:#f6f7f9;border-radius:5px;padding:6px 8px;display:none}
.def.show{display:block}
.searchbar{display:flex;gap:6px;margin-bottom:8px}.searchbar input{flex:1;padding:5px 7px;border:1px solid var(--line);border-radius:5px}
.searchbar select{padding:5px;border:1px solid var(--line);border-radius:5px}
textarea{width:100%;font:inherit;border:1px solid var(--line);border-radius:6px;padding:6px;min-height:44px}
.curbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.cui{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--blue)}
.now{font-size:13px}.empty{color:var(--mut);padding:30px;text-align:center}
.stylist{max-height:340px;overflow:auto}
.styrow{border:1px solid var(--line);border-radius:6px;padding:5px 8px;margin-bottom:5px;font-size:12.5px}
.styrow.acc{border-color:var(--green);background:#f4fbf6}
.stytree{font-family:ui-monospace,Menlo,monospace;color:var(--mut);margin-right:6px}
.styrow button{float:right}
.evrow{margin:2px 0;line-height:1.5}
.mut{color:var(--mut)}
.vocab{display:inline-block;background:#eef3ff;color:#2456c9;border:1px solid #cfe;border-radius:4px;padding:0 4px;margin:1px;font-size:11px}
.vocab.obs{background:#f3f3f5;color:#9aa1ac;border-color:#e2e5ea}
.vocab sub{font-size:9px;opacity:.7}
.evtop{font-size:12.5px;margin-bottom:4px}
.evsec{margin:6px 0 2px;border-top:1px solid var(--line);padding-top:5px}
.evh{font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--mut);margin-bottom:3px}
button.mini{font-size:11px;padding:1px 6px}.evh button.mini{float:right;text-transform:none;letter-spacing:0}
.et{border-collapse:collapse;width:100%;font-size:12px}
.et th{text-align:left;color:var(--mut);font-weight:500;border-bottom:1px solid var(--line);padding:2px 8px 2px 0;white-space:nowrap}
.et td{padding:2px 8px 2px 0;vertical-align:top;border-bottom:1px solid #f1f3f6}
.et tr.obs td{color:var(--grey)}
.et tr.axisrow td{border-top:1px solid var(--line);color:var(--blue)}
.stn{font-family:ui-monospace,Menlo,monospace;color:var(--mut)}
.dir.up{color:var(--green);white-space:nowrap}.dir.down{color:var(--blue);white-space:nowrap}
.badge.bad{background:#fdecec;color:#b00;border-color:#f3c0c0}
.subtree{margin-top:5px;font-size:12px;max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:6px;padding:6px}
.stn-node{padding:1px 2px;border-radius:3px}
.stn-kids{margin-left:12px;border-left:1px solid var(--line);padding-left:8px}
.stn-tree{font-family:ui-monospace,Menlo,monospace;color:var(--mut);font-size:10.5px;margin-right:4px}
.stn-node.hl{background:#eaf6ef;font-weight:600}
.stn-node.ax{color:var(--blue)}
.mini2{font-size:11px;color:var(--mut);margin-bottom:3px}.mini2 a{color:var(--blue);text-decoration:none}
.et .orh td{background:var(--hd,#eef2f7);font-weight:600;font-family:monospace;font-size:11px}
.otherbox{margin-top:4px}
.axrow{display:flex;gap:8px;align-items:center;margin:5px 0}
.axrow label{width:72px;color:var(--mut);font-size:12px;text-align:right}
.axrow input{flex:1;padding:5px 7px;border:1px solid var(--line);border-radius:5px;font:inherit}
.axrow input[readonly]{background:#f2f4f7;color:var(--mut)}
.axtree{margin-top:5px;padding-top:5px;border-top:1px dashed var(--line)}
</style></head><body>
<div id="top">
  <h1>GEM &rarr; UMLS adjudication</h1>
  <div class="counts" id="counts"></div>
  <button id="newaxis" class="primary">+ New axis</button>
  <button id="rebuild">Rebuild crosswalk</button>
  <span id="msg"></span>
</div>
<div id="wrap">
  <div id="list">
    <div id="filter">
      <select id="fstatus">
        <option value="all">All</option>
        <option value="needs">Needs attention (review/uncurated)</option>
        <option value="mapped">Mapped</option>
        <option value="unmapped">Unmapped</option>
        <option value="curated">Curated</option>
        <option value="auto">Auto (not curated)</option>
      </select>
      <input id="ftext" placeholder="filter token...">
    </div>
    <div id="items"></div>
  </div>
  <div id="detail"><div class="empty">Select an entry on the left.</div></div>
</div>
<script>
let STATE=null, SEL=null, AXB=null;
const $=s=>document.querySelector(s);
const esc=s=>(s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function msg(t){$('#msg').textContent=t||'';}
async function loadState(){const r=await fetch('/api/state');STATE=await r.json();renderCounts();renderList();if(SEL)renderDetail(SEL);}
function renderCounts(){const c=STATE.counts;$('#counts').innerHTML=
  `<span>total <b>${c.total}</b></span><span>mapped <b>${c.mapped}</b></span>`+
  `<span>unmapped <b>${c.unmapped}</b></span><span>review <b>${c.review}</b></span><span>curated <b>${c.curated||0}</b></span>`;}
function passFilter(e){const f=$('#fstatus').value,t=$('#ftext').value.toLowerCase();
  if(t && !(String(e.token||'axis')+' '+e.dimension).toLowerCase().includes(t))return false;
  if(f==='all')return true;if(f==='mapped')return e.status==='mapped';if(f==='unmapped')return e.status==='unmapped';
  if(f==='curated')return e.curated;if(f==='auto')return e.status==='mapped'&&!e.curated;
  if(f==='needs')return e.status==='review'||!e.curated;return true;}
function renderList(){const box=$('#items');box.innerHTML='';let dim=null;
  STATE.entries.filter(passFilter).forEach(e=>{
    if(e.dimension!==dim){dim=e.dimension;const h=document.createElement('div');h.className='dimhdr';h.textContent=dim;box.appendChild(h);}
    const d=document.createElement('div');d.className='item'+(SEL&&SEL.key===e.key?' sel':'');
    d.innerHTML=`<span class="dot ${e.status}"></span><span><span class="tk">${esc(e.token||'(axis)')}</span>`+
      (e.kind==='axis'?' <span class="badge" style="background:#eef;color:#33c;border-color:#ccd">axis</span>':'')+
      (e.curated?' <span class="badge">curated</span>':'')+
      `<div class="mini">${e.status==='mapped'?esc(e.sty_name?e.sty_name+' ('+e.sty_tui+')':(e.matched_name||e.cui||'')):e.status}</div></span>`;
    d.onclick=()=>{SEL=e;renderList();renderDetail(e);};box.appendChild(d);});}
function candHTML(c,key){const acc=SEL&&SEL.decision_cui===c.cui;
  return `<div class="cand ${acc?'acc':''}"><div class="row"><span class="n">${esc(c.name)} <span class="cui">${esc(c.cui)}</span></span>`+
    `<button onclick="loadDef('${c.cui}',this)">info</button>`+
    `<button class="ok" onclick="decide('accept','${c.cui}')">${acc?'✓ accepted':'accept'}</button></div>`+
    `<div class="sty">${esc((c.sty||c.semantic_types||[]).join(', '))}${c.src||c.root_source?' · '+esc(c.src||c.root_source):''}</div>`+
    `<div class="def"></div></div>`;}
function renderDetail(e){SEL=STATE.entries.find(x=>x.key===e.key)||e;e=SEL;
  if(e.kind==='axis') return renderAxisBuilder(e);
  const cur=e.status==='mapped'?`<span class="now">mapped &rarr; <b>${esc(e.matched_name)}</b> <span class="cui">${esc(e.cui)}</span>`+
      (e.curated?` <span class="badge">${e.fetched?'curated·fetched':'curated'}</span>`:' (auto)')+`</span>`:
    e.status==='unmapped'?`<span class="now">unmapped${e.curated?' <span class="badge">curator</span>':''}</span>`:
    `<span class="now">review</span>`;
  const filt=e.dim_sty_tui?`<span class="badge">search constrained to axis type ${esc(e.dim_sty_tui)}</span>`:'<span class="mini">axis untyped — search unconstrained</span>';
  $('#detail').innerHTML=`
   <h2>${esc(e.token||'(axis)')}</h2><div class="sub">${esc(e.dimension)} · ${esc(e.kind)} · query <b>${esc(e.query)}</b></div>
   <div class="card"><h3>GEM meaning</h3><div class="mean">${esc(e.meaning)||'<span class=mini>(no gloss)</span>'}</div></div>
   <div class="card"><h3>Current decision</h3>${cur}${e.error?` <span style="color:#b00">${esc(e.error)}</span>`:''}
     <div class="curbar" style="margin-top:8px">
       <button class="warn" onclick="decide('unmapped')">Mark unmapped</button>
       <button onclick="decide('clear')">Clear decision</button>
       ${e.note?`<span class="mini">note: ${esc(e.note)}</span>`:''}
     </div>
     <textarea id="note" placeholder="optional note / rationale">${esc(e.note||'')}</textarea>
   </div>
   <div class="card"><h3>Query candidates (${e.candidates.length})</h3>${e.candidates.map(c=>candHTML(c,e.key)).join('')||'<span class=mini>none returned</span>'}</div>
   <div class="card"><h3>Search the Metathesaurus &nbsp; ${filt}</h3>
     <div class="searchbar"><input id="sq" placeholder="concept term..." value="${esc(e.token&&e.token!=='(axis)'?e.token.replace(/_/g,' ').toLowerCase():e.query)}">
       <select id="ssab"><option value="">all sources</option><option>MSH</option><option>NCI</option><option>SNOMEDCT_US</option><option>GO</option><option>HPO</option></select>
       <button class="primary" onclick="runSearch()">Search</button></div>
     <div id="sresults"></div></div>`;
  $('#sq').addEventListener('keydown',ev=>{if(ev.key==='Enter')runSearch();});}
function newAxis(){SEL=null;AXB={dimension:'',query:'',note:'',tui:null,isnew:true};
  renderList();loadSemTypes().then(()=>renderAxisBuilder());}
function renderAxisBuilder(e){
  // e: an existing axis entry to modify; omit for a brand-new axis from scratch.
  if(e){AXB={dimension:e.dimension,query:e.axis_query||e.query||'',note:e.axis_note||e.note||'',
             tui:e.sty_tui||null,isnew:!e.in_inventory};}
  else if(!AXB){AXB={dimension:'',query:'',note:'',tui:null,isnew:true};}
  const ro=AXB.isnew?'':'readonly';
  $('#detail').innerHTML=`
   <h2>${AXB.isnew?'New axis':esc(AXB.dimension)} <span class="mini">(axis)</span></h2>
   <div class="sub">An axis maps a dimension to a UMLS <b>semantic type</b>; its subtree becomes the type filter for every value search in this dimension. Concept-level relations do not apply here — those belong to values.</div>
   <div class="card"><h3>Definition</h3>
     <div class="axrow"><label>dimension</label><input id="axdim" value="${esc(AXB.dimension)}" ${ro} placeholder="e.g. resolution"></div>
     <div class="axrow"><label>query</label><input id="axq" value="${esc(AXB.query)}" placeholder="seed query, e.g. Spatial concept"><button onclick="axbRun()">Run query &rarr;</button></div>
     <div class="axrow"><label>note</label><input id="axnote" value="${esc(AXB.note)}" placeholder="what this axis means"></div></div>
   <div class="card"><h3>Axis semantic type</h3><div id="axsel"></div>
     <div class="curbar" style="margin-top:8px"><button class="ok" onclick="axbSave()">${AXB.isnew?'Create axis':'Save axis'}</button>
       <span class="mini">writes to the workspace inventory</span></div></div>
   <div class="card"><h3>Query &rarr; semantic types <span class="mini">an axis maps to a type, not a concept — what type should this axis be?</span></h3>
     <div id="axprev"><span class="mini">Run the query to see the semantic types of the matching concepts; click one to use it as the axis type.</span></div></div>
   <div class="card"><h3>Pick / browse a semantic type</h3>
     <div class="searchbar"><input id="styq" placeholder="filter by name / TUI / tree..."></div>
     <div id="styresults" class="stylist"></div></div>`;
  ['axdim','axq','axnote'].forEach(id=>{const el=$('#'+id);if(el)el.addEventListener('input',()=>{
     AXB.dimension=$('#axdim').value;AXB.query=$('#axq').value;AXB.note=$('#axnote').value;});});
  $('#axq').addEventListener('keydown',ev=>{if(ev.key==='Enter')axbRun();});
  $('#styq').addEventListener('input',axbPicker);
  loadSemTypes().then(()=>{axbPicker();axbRenderSel();});}
async function axbRun(){const q=(($('#axq')||{}).value||'').trim();const box=$('#axprev');if(!box)return;
  if(!q){box.innerHTML='<span class="mini">enter a query first</span>';return;}
  box.innerHTML='searching UMLS...';
  const j=await (await fetch('/api/search?string='+encodeURIComponent(q))).json();
  if(j.error){box.innerHTML='<span style="color:#b00">'+esc(j.error)+'</span>';return;}
  const res=(j.results||[]).slice(0,60);
  if(!res.length){box.innerHTML='<span class="mini">no results — offline (no key), or no match. You can still pick a type directly below.</span>';return;}
  // aggregate the semantic types of the matching concepts (name -> TUI via the
  // Semantic Network we already loaded); an axis is one of THESE types.
  const norm=s=>(s||'').toLowerCase(), byT={};
  res.forEach(c=>(c.semantic_types||[]).forEach(nm=>{
    const t=(SEMTYPES||[]).find(x=>norm(x.name)===norm(nm));if(!t)return;
    const g=byT[t.tui]||(byT[t.tui]={tui:t.tui,name:t.name,tree:t.tree,n:0,ex:[]});
    g.n++;if(g.ex.length<5)g.ex.push(c.name);}));
  const types=Object.values(byT).sort((a,b)=>b.n-a.n);
  if(!types.length){box.innerHTML='<span class="mini">'+res.length+' concepts matched but none carried a recognised semantic type. Pick a type directly below.</span>';return;}
  const rows=types.map(t=>`<div class="styrow ${t.tui===AXB.tui?'acc':''}"><span class="stytree">${esc(t.tree)}</span> ${esc(t.name)} <span class="cui">${esc(t.tui)}</span> <span class=mut>&times;${t.n}</span>`+
    `<button class="ok" onclick="axbSet('${t.tui}')">${t.tui===AXB.tui?'✓ axis type':'use as axis type'}</button>`+
    `<button class="mini" onclick="stnToggle(this,'${t.tui}')">tree</button>`+
    `<div class="mini">e.g. ${esc(t.ex.join(', '))}</div></div>`).join('');
  box.innerHTML=`<div class="mini">${types.length} semantic type${types.length===1?'':'s'} across ${res.length} matching concepts — click one to set the axis type:</div><div class="stylist">${rows}</div>`;}
function axbRenderSel(){const box=$('#axsel');if(!box)return;const t=(SEMTYPES||[]).find(x=>x.tui===AXB.tui);
  if(!t){box.innerHTML='<span class="mini">no type chosen — pick or browse one below</span>';return;}
  const sub=(SEMTYPES||[]).filter(x=>x.tree===t.tree||x.tree.startsWith(t.tree+'.'));
  box.innerHTML=`<span class="now">&rarr; <b>${esc(t.name)}</b> <span class="cui">${esc(t.tui)} · ${esc(t.tree)}</span></span>`+
    `<div class="mini">value searches constrained to <b>${sub.length}</b> semantic type${sub.length===1?'':'s'} (this type + ${sub.length-1} descendant${sub.length-1===1?'':'s'})</div>`+
    (t.definition?`<div class="def show">${esc(t.definition)}</div>`:'')+
    `<div class="subtree" style="margin-top:6px">${stnPlaceHTML(t.tui)}</div>`;}
function axbPicker(){const box=$('#styresults');if(!box)return;const q=(($('#styq')||{}).value||'').toLowerCase();
  box.innerHTML=(SEMTYPES||[]).filter(t=>!q||(t.name+' '+t.tui+' '+t.tree).toLowerCase().includes(q)).slice(0,80).map(t=>
    `<div class="styrow ${t.tui===AXB.tui?'acc':''}"><span class="stytree">${esc(t.tree)}</span> ${esc(t.name)} <span class="cui">${esc(t.tui)}</span>`+
    `<button class="ok" onclick="axbSet('${t.tui}')">${t.tui===AXB.tui?'✓ chosen':'choose'}</button>`+
    `<button class="mini" onclick="stnToggle(this,'${t.tui}')">tree</button>`+
    (t.definition?`<div class="def show">${esc(t.definition)}</div>`:'')+`</div>`).join('');}
function axbSet(tui){AXB.tui=tui;axbRenderSel();axbPicker();}
// A type's place in the Semantic Network: the ancestor spine (by tree-number
// prefix) down to its parent, the parent's children (siblings), and the type's
// own descendants -- the type highlighted. Every node is clickable to select it.
function stnPlaceHTML(tui){const t=(SEMTYPES||[]).find(x=>x.tui===tui);if(!t)return '<i>type not found</i>';
  const dep=s=>s.split('.').length;
  const node=(n,inner)=>`<div class="stn-node${n.tui===tui?' hl':''}"><span class="stn-tree">${esc(n.tree)}</span> `+
    `<a href="#" onclick="axbSet('${n.tui}');return false">${esc(n.name)}</a> <span class=cui>${esc(n.tui)}</span>`+
    (inner?`<div class="stn-kids">${inner}</div>`:'')+`</div>`;
  const kidsOf=n=>(SEMTYPES||[]).filter(x=>x.tree.startsWith(n.tree+'.')&&dep(x.tree)===dep(n.tree)+1)
                                .sort((a,b)=>a.tree<b.tree?-1:1);
  const sub=n=>node(n,kidsOf(n).map(sub).join(''));            // n + all descendants
  const segs=t.tree.split('.'), chain=[];
  for(let i=1;i<segs.length;i++){const a=(SEMTYPES||[]).find(x=>x.tree===segs.slice(0,i).join('.'));if(a)chain.push(a);}
  const parent=chain.length?chain[chain.length-1]:null;
  let core;
  if(parent){core=node(parent,kidsOf(parent).map(s=>s.tui===t.tui?sub(t):node(s,'')).join(''));
    for(let i=chain.length-2;i>=0;i--)core=node(chain[i],core);}   // wrap remaining ancestors
  else core=sub(t);
  return `<div class="stn-tree">${core}</div>`;}
function stnToggle(btn,tui){const row=btn.closest('.styrow')||btn.parentElement;
  const box=row.querySelector(':scope > .axtree');
  if(box){box.remove();return;}
  const d=document.createElement('div');d.className='axtree';d.innerHTML=stnPlaceHTML(tui);row.appendChild(d);}
async function axbSave(){AXB.dimension=($('#axdim')||{}).value||AXB.dimension;AXB.query=($('#axq')||{}).value||AXB.query;AXB.note=($('#axnote')||{}).value||AXB.note;
  if(!AXB.dimension.trim()){msg('dimension name required');return;}
  msg('saving axis...');
  const j=await (await fetch('/api/axis',{method:'POST',headers:{'Content-Type':'application/json'},
     body:JSON.stringify({dimension:AXB.dimension,semantic_type:AXB.tui||'',query:AXB.query,note:AXB.note})})).json();
  if(j.error){msg('error: '+j.error);return;}
  const dim=AXB.dimension.trim();
  msg('saved axis '+dim+(AXB.tui?(' → '+AXB.tui):'')+' — Rebuild to (re)generate value candidates');
  await loadState();const ax=STATE.entries.find(x=>x.kind==='axis'&&x.dimension===dim);
  if(ax){SEL=ax;renderList();renderAxisBuilder(ax);}}
let SEMTYPES=null;
async function loadSemTypes(){if(!SEMTYPES){SEMTYPES=(await (await fetch('/api/semantictypes')).json()).types;}return SEMTYPES;}
async function loadDef(cui,btn){const box=btn.closest('.cand').querySelector('.def');
  if(box.classList.contains('show')){box.classList.remove('show');return;}
  box.innerHTML='loading concept evidence...';box.classList.add('show');
  const axis=SEL&&SEL.dim_sty_tui?('&axis='+SEL.dim_sty_tui):'';
  const j=await (await fetch('/api/concept?cui='+cui+axis)).json();
  await loadSemTypes();
  renderInfo(box,cui,j.evidence||{},j.definitions||[]);}
function renderInfo(box,cui,e,defs){
  if(e.error){box.innerHTML='<i>'+esc(e.error)+'</i>';return;}
  const spec=(e.sty_path&&e.sty_path[0])||{}, axis=e.axis_sty;
  const pathRows=(e.sty_path||[]).map((p,i)=>`<tr><td>${i?'<span class=mut>&uarr;</span>':'<b>STY</b>'}</td><td>${esc(p.name)}</td><td class=cui>${esc(p.tui)}</td><td class=stn>${esc(p.tree)}</td></tr>`).join('');
  const axbadge=axis?(e.under_axis?' <span class="badge">in axis branch</span>':' <span class="badge bad">outside axis branch</span>'):'';
  const styBlock=`<div class="evsec"><div class="evh">Semantic type${axbadge}<button class="mini" onclick="toggleSubtree(this,'${esc(spec.tui||'')}','${axis?esc(axis.tui):''}')">subtree</button></div>`+
    `<table class="et"><tr><th></th><th>STY</th><th>TUI</th><th>STN</th></tr>${pathRows}`+
    (axis?`<tr class=axisrow><td><b>axis</b></td><td>${esc(axis.name)}</td><td class=cui>${esc(axis.tui)}</td><td class=stn>${esc(axis.stn)}</td></tr>`:'')+
    `</table><div class="subtree" style="display:none"></div></div>`;
  const vrows=(e.atom_rows||[]).map(a=>`<tr class="${a.obsolete?'obs':''}"><td>${esc(a.sab)}</td><td>${esc(a.str)}</td><td>${esc(a.tty)}</td><td class=cui>${esc(a.code)}</td></tr>`).join('');
  const vocBlock=`<div class="evsec"><div class="evh">Vocabularies (${(e.sabs||[]).length} sources, English)</div><table class="et"><tr><th>SAB</th><th>STR</th><th>TTY</th><th>Code</th></tr>${vrows||'<tr><td colspan=4><i>none</i></td></tr>'}</table></div>`;
  const rid=r=>esc(r.cui||r.code||'');
  const rrows=(e.relations||[]).map(r=>`<tr><td class="dir ${r.dir}">${r.dir==='up'?'&uarr; is_a':'&darr; is_a'}</td><td>${esc(r.name)}</td><td class=cui>${rid(r)}</td><td>${esc((r.sabs||[]).join(', '))}</td></tr>`).join('');
  const relBlock=`<div class="evsec"><div class="evh">Hierarchy (is_a)</div><table class="et"><tr><th>dir</th><th>concept</th><th>id</th><th>sources</th></tr>${rrows||'<tr><td colspan=4><i>no is_a parents or children in English vocabularies</i></td></tr>'}</table></div>`;
  const org=(e.other_relations||[]);
  const orInner=org.map(g=>{
    const items=g.items.map(it=>`<tr><td>${esc(it.name)}</td><td class=cui>${rid(it)}</td><td>${esc((it.sabs||[]).join(', '))}</td></tr>`).join('');
    const more=g.n>g.items.length?`<tr><td colspan=3 class=mut>+${g.n-g.items.length} more</td></tr>`:'';
    return `<tr class=orh><td colspan=3>${esc(g.rela)} <span class=mut>(${g.n})</span></td></tr>${items}${more}`;}).join('');
  const otherBlock=org.length?`<div class="evsec"><div class="evh">Other relations<button class="mini" data-k="${org.length}" onclick="toggleOther(this)">show ${org.length} kinds</button></div><div class="otherbox" style="display:none"><table class="et"><tr><th>concept</th><th>id</th><th>sources</th></tr>${orInner}</table></div></div>`:'';
  const df=(defs||[]).map(d=>`<b>[${esc(d.source)}]</b> ${esc(d.value)}`).join('<br>')||'<i>no definition</i>';
  const rollBlock=`<div class="evsec"><div class="evh">Rollup<button class="mini" onclick="loadRollup(this.closest('.evsec').querySelector('.rollbox'),'${cui}')">roll up &darr;</button></div><div class="rollbox"></div></div>`;
  box.innerHTML=`<div class="evtop"><b>${esc(e.name)}</b> <span class=cui>${esc(cui)}</span> &middot; status ${esc(e.status||'?')} &middot; ${e.atom_count||0} atoms</div>`+
    styBlock+vocBlock+relBlock+otherBlock+
    `<div class="evsec"><div class="evh">Definition</div><div class="evrow">${df}</div></div>`+rollBlock;}
function toggleOther(btn){const box=btn.closest('.evsec').querySelector('.otherbox');const show=box.style.display==='none';box.style.display=show?'block':'none';btn.textContent=(show?'hide ':'show ')+btn.dataset.k+' kinds';}
function toggleSubtree(btn,specTui,axisTui){const box=btn.closest('.evsec').querySelector('.subtree');
  if(box.style.display!=='none'){box.style.display='none';return;}
  box.style.display='block';
  const root=axisTui||specTui, rt=(SEMTYPES||[]).find(t=>t.tui===root);
  if(!rt){box.innerHTML='<i>semantic type not found</i>';return;}
  const inSub=(SEMTYPES||[]).filter(t=>t.tree===rt.tree||t.tree.startsWith(rt.tree+'.'));
  const dep=s=>s.split('.').length;
  const render=n=>{const kids=inSub.filter(t=>t.tree.startsWith(n.tree+'.')&&dep(t.tree)===dep(n.tree)+1);
    const hl=n.tui===specTui?' hl':(n.tui===axisTui?' ax':'');
    return `<div class="stn-node${hl}"><span class="stn-tree">${esc(n.tree)}</span> ${esc(n.name)} <span class=cui>${esc(n.tui)}</span>`+
      (kids.length?`<div class="stn-kids">${kids.map(render).join('')}</div>`:'')+`</div>`;};
  box.innerHTML=render(rt);}
async function loadRollup(box,cui,sab){box.innerHTML='rolling up is_a ancestors...';
  const j=await (await fetch('/api/rollup?cui='+cui+(sab?'&use_sab='+encodeURIComponent(sab):''))).json();
  const rows=(j.rollup||[]).map(a=>`<tr><td>${esc(a.name)}</td><td class=cui>${esc(a.code)}</td><td>${esc(a.sab)}</td></tr>`).join('');
  const opts=j.sabs||[];
  const nav=opts.length?`<div class=mini2>vocabulary: <a href="#" data-cui="${cui}" onclick="rollNav(this,'');return false">auto</a>${opts.map(s=>` &middot; <a href="#" data-cui="${cui}" onclick="rollNav(this,'${esc(s)}');return false">${esc(s)}</a>`).join('')}${sab?' &mdash; <b>'+esc(sab)+'</b>':''}</div>`:'';
  box.innerHTML=nav+`<table class="et"><tr><th>is_a ancestor</th><th>code</th><th>vocab</th></tr>${rows||'<tr><td colspan=3><i>no is_a ancestors in English vocabularies</i></td></tr>'}</table>`;}
function rollNav(a,sab){loadRollup(a.closest('.rollbox'),a.dataset.cui,sab||null);}
async function runSearch(){const q=$('#sq').value,sab=$('#ssab').value;const box=$('#sresults');box.innerHTML='searching...';
  const stys=SEL.dim_sty_filter||'';
  const url='/api/search?string='+encodeURIComponent(q)+(sab?'&sabs='+sab:'')+(stys?'&stys='+encodeURIComponent(stys):'');
  const r=await fetch(url);const j=await r.json();
  if(j.error){box.innerHTML='<span style="color:#b00">'+esc(j.error)+'</span>';return;}
  box.innerHTML=(j.results||[]).slice(0,15).map(c=>candHTML(c,SEL.key)).join('')||'<span class=mini>no results (within axis type)</span>';}
async function decide(verdict,cui){const note=($('#note')||{}).value||'';
  const body={key:SEL.key,verdict};if(cui)body.cui=cui;if(note)body.note=note;
  msg('saving...');const r=await fetch('/api/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json();if(j.error){msg('error: '+j.error);return;}msg('saved '+SEL.key+' ('+verdict+') — Rebuild to refresh status');
  await loadState();}
$('#rebuild').onclick=async()=>{msg('rebuilding (querying UMLS)...');const r=await fetch('/api/rebuild',{method:'POST'});const j=await r.json();
  if(j.error){msg('error: '+j.error);return;}msg('rebuilt: '+JSON.stringify(j.counts));await loadState();};
$('#newaxis').onclick=newAxis;
$('#fstatus').onchange=renderList;$('#ftext').oninput=renderList;
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
    print(f"Adjudication UI running at {url}  (workspace: {DATA_DIR})  (Ctrl-C to stop)")
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
