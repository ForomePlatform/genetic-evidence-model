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

* Curate VALUES. "Add value" defines one (token + the query to search UMLS
  for, an honest prior, an optional source hint and note); the row controls
  edit or remove it. Values are written to the same inventory as the axes and
  the dimension is re-resolved on the spot, so a workspace can be taken from an
  empty directory to a built crosswalk without hand-editing YAML.

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
API with your key and write files. The key is read from UMLS_API_KEY, the repo
.envrc, or the per-user key file (~/.config/forome-gem/umls_api_key, written by
the Connect UMLS dialog) and never sent to the browser; the browser calls local
/api/* endpoints that proxy UMLS.

A key is required to CHANGE anything. Without one the Studio still starts and
the workspace is fully browsable -- dimensions, values, axes, recorded
decisions -- but every write answers needs_key and every control that would
write is disabled, because an axis, a value or a decision the Metathesaurus has
not confirmed is not a mapping. The browser then walks the curator through
obtaining a key (UTS sign-up, license approval, profile page) rather than
failing silently.

Usage:
    export UMLS_API_KEY=...            # or .envrc / key file, or the Studio's
                                       # Connect UMLS dialog
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

# Offline fallback for the vocabulary picker (no key / no network): the
# sources that matter for this crosswalk. Live runs use the full UTS list.
BUILTIN_SABS = {
    "MSH": "Medical Subject Headings", "MTH": "UMLS Metathesaurus names",
    "NCI": "NCI Thesaurus", "SNOMEDCT_US": "SNOMED CT, US Edition",
    "HPO": "Human Phenotype Ontology", "GO": "Gene Ontology",
    "CSP": "CRISP Thesaurus", "MDR": "MedDRA", "OMIM": "Online Mendelian Inheritance in Man",
    "LNC": "LOINC", "RXNORM": "RxNorm", "ICD10CM": "ICD-10-CM", "CHV": "Consumer Health Vocabulary",
    "NCBI": "NCBI Taxonomy", "RCD": "Read Codes", "SNMI": "SNOMED International 1998",
    "PDQ": "Physician Data Query", "AIR": "AI/RHEUM", "NCI_NCI-GLOSS": "NCI Dictionary of Cancer Terms",
}

ADJ_HEADER = [
    "# Curator adjudications for the UMLS crosswalk review/unmapped entries.",
    "# Applied by build_umls_crosswalk.py AFTER querying. 'accept' is used only if the",
    "# CUI was among the query's candidates OR the harness can fetch it live from UMLS;",
    "# the harness never fabricates a concept the curator merely named. 'unmapped: true'",
    "# records a considered 'no faithful UMLS concept' (honest finding). Edited via",
    "# mapping/adjudicate_ui.py.",
]

# ---- structured rationale (shared schema across the mapping workstreams) ----
# Stored per entry alongside accept/unmapped/note:
#   relation: how the CUI relates to the GEM token (accepts), or none (unmapped)
#   rejected: [{cui, name, sab, fails, why}]  fails = criterion code A-D
#   protocol: {queries, scopes, match, sabs, umls}  what was actually searched
RELATIONS = ("exact", "close", "broader", "narrower", "related", "none")
CRITERIA = {
    "A": "denotation — the concept denotes a different thing or relation than "
         "the GEM token (e.g. a measurand degree vs an epistemic degree)",
    "B": "granularity — only a broader/narrower concept exists and the gap is "
         "not acceptable as a proxy",
    "C": "set membership — cannot serve as a point of the token's "
         "scale/enumeration (not disjoint from / ordered with its siblings)",
    "D": "domain sense — right words, wrong domain or context (e.g. an IPSS-R "
         "risk category named 'High')",
}
SCOPES = ("axis", "all")
MATCH_TYPES = ("words", "exact", "normalizedWords", "normalizedString", "partial")
RATIONALE_KEYS = ("relation", "rejected", "protocol")
RATIONALE_MAXLEN = 300      # cap on every free-text rationale string
RATIONALE_MAXITEMS = 50     # cap on every rationale list
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}")   # CUI / SAB shape

# Where a dimension's values live in the inventory: schema-enumerated tokens
# under `values`, conventions on an open dimension under `common_values`.
VALUE_SEQS = {"value": "values", "common_value": "common_values"}
EXPECTS = ("likely", "uncertain", "unlikely")   # the curator's prior on a value
# A token is an identifier in the curator's vocabulary, not prose: GEM writes
# UPPER_SNAKE, other workspaces may not, so the shape is permissive but excludes
# whitespace (the adjudication key is "dimension/token").
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}")

# ---- "what still needs a curator's eyes": ONE definition (entry_needs), computed
# by the server and consumed as data by the whole UI -- the rail badges, the Home
# worklist, the values-table filter, the value view's "next" button. Fixed order.
# (code, short label, description, scope)
NEED_CODES = (
    ("unbuilt", "not resolved",
     "in the inventory but not in the crosswalk — rebuild the dimension to "
     "query UMLS for it", "value"),
    ("review", "review",
     "in review — the harness found candidates but no faithful match", "value"),
    ("unconfirmed", "unconfirmed",
     "auto-mapped by the harness, not yet confirmed by a curator", "value"),
    ("unresolved", "unresolved",
     "no candidates from the harness query — search wider (this is a gap, not a verdict)",
     "value"),
    ("no-rationale", "no rationale",
     "recorded as unmapped without an argument", "value"),
    ("untyped", "untyped axis",
     "axis has no semantic type — value searches run unconstrained", "axis"),
)
NEED_LABELS = {c: {"label": l, "desc": d, "scope": s} for c, l, d, s in NEED_CODES}


def _rs(x, what: str) -> str:
    """A rationale string: must be a scalar, stripped, capped at RATIONALE_MAXLEN."""
    if x is None:
        return ""
    if isinstance(x, (dict, list)):
        raise ValueError(f"{what} must be a string")
    return str(x).strip()[:RATIONALE_MAXLEN]


def _rlist(x, what: str) -> list:
    if x is None:
        return []
    if not isinstance(x, list):
        raise ValueError(f"{what} must be a list")
    if len(x) > RATIONALE_MAXITEMS:
        raise ValueError(f"{what}: at most {RATIONALE_MAXITEMS} items (got {len(x)})")
    return list(x)


def validate_rationale(verdict: str, data: dict) -> dict:
    """Validate the optional structured-rationale keys of a /api/decide body
    and return the cleaned subset to store ({} when none were given).

    * relation  -- one of RELATIONS; 'none' is required for unmapped verdicts
                   and refused for accepts. Unmapped verdicts that carry a
                   rejected list or protocol default to relation: none.
    * rejected  -- list of {cui, name, sab, fails, why}: cui and fails (A-D)
                   are mandatory, the rest optional; strings are capped.
    * protocol  -- {queries, scopes, match, sabs, umls}: scopes/match values
                   must come from SCOPES/MATCH_TYPES; unknown keys are dropped.
    Raises ValueError with a curator-readable message on a malformed body."""
    out: dict = {}
    rel = data.get("relation")
    if rel is not None:
        if not isinstance(rel, str) or rel not in RELATIONS:
            raise ValueError(f"relation must be one of {', '.join(RELATIONS)}")
        if verdict == "unmapped" and rel != "none":
            raise ValueError("an unmapped entry takes relation: none")
        if verdict != "unmapped" and rel == "none":
            raise ValueError("relation: none is only valid for unmapped entries")
        out["relation"] = rel
    elif verdict == "unmapped" and (data.get("rejected") is not None
                                    or data.get("protocol") is not None):
        out["relation"] = "none"

    if data.get("rejected") is not None:
        rows = []
        for i, item in enumerate(_rlist(data["rejected"], "rejected")):
            if not isinstance(item, dict):
                raise ValueError(f"rejected[{i}] must be an object")
            cui = _rs(item.get("cui"), "rejected cui")
            if not cui or not _ID_RE.fullmatch(cui):
                raise ValueError(f"rejected[{i}]: a CUI is required")
            fails = _rs(item.get("fails"), "rejected fails").upper()
            if fails not in CRITERIA:
                raise ValueError(f"rejected[{i}] ({cui}): fails must be one of "
                                 f"{', '.join(CRITERIA)}")
            row = {"cui": cui, "fails": fails}
            for k in ("name", "sab", "why"):
                v = _rs(item.get(k), f"rejected {k}")
                if v:
                    row[k] = v
            rows.append(row)
        out["rejected"] = rows

    if data.get("protocol") is not None:
        proto = data["protocol"]
        if not isinstance(proto, dict):
            raise ValueError("protocol must be an object")
        clean: dict = {}
        for k, allowed in (("queries", None), ("scopes", SCOPES),
                           ("match", MATCH_TYPES), ("sabs", None)):
            vals = []
            for v in _rlist(proto.get(k), f"protocol {k}"):
                v = _rs(v, f"protocol {k}")
                if not v:
                    continue
                if k == "sabs":
                    v = v.upper()
                if allowed is not None and v not in allowed:
                    raise ValueError(f"protocol {k}: {v!r} is not one of "
                                     f"{', '.join(allowed)}")
                if v not in vals:
                    vals.append(v)
            if vals:
                clean[k] = vals
        umls = _rs(proto.get("umls"), "protocol umls")
        if umls:
            clean["umls"] = umls
        out["protocol"] = clean
    return out


# Per-user key file written by the Studio's "Connect UMLS" dialog (mode 0600),
# so a pip-installed Studio on a machine without a repo checkout keeps its key
# between runs. Env and the repo .envrc take precedence.
KEY_FILE = (Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
            / "forome-gem" / "umls_api_key")

UTS_SIGNUP_URL = "https://uts.nlm.nih.gov/uts/signup-login"
UTS_PROFILE_URL = "https://uts.nlm.nih.gov/uts/profile"

# The Studio's usage guide, opened by the ? control in the brand row. Kept as
# ONE constant because the document's home is provisional -- set
# $GEM_STUDIO_HELP_URL to point a deployment at its own copy.
HELP_URL = os.environ.get("GEM_STUDIO_HELP_URL") or (
    "https://github.com/ForomePlatform/genetic-evidence-model"
    "/blob/master/docs/STUDIO.md")


def find_api_key() -> tuple[str, str]:
    """(key, source) -- source is 'env', '.envrc', 'key file', or '' when none."""
    k = os.environ.get("UMLS_API_KEY", "")
    if k:
        return k, "env"
    envrc = H.BASE / ".envrc"
    if envrc.is_file():
        for line in envrc.read_text().splitlines():
            m = re.match(r"\s*export\s+UMLS_API_KEY=(.+)", line)
            if m:
                return m.group(1).strip().strip("\"'"), ".envrc"
    try:
        if KEY_FILE.is_file():
            k = KEY_FILE.read_text().strip()
            if k:
                return k, "key file"
    except OSError:
        pass
    return "", ""


def api_key() -> str:
    return find_api_key()[0]


def remember_api_key(key: str) -> Path:
    """Store the key for this user only (dir 0700, file 0600)."""
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        KEY_FILE.parent.chmod(0o700)
    except OSError:
        pass
    KEY_FILE.write_text(key.strip() + "\n")
    KEY_FILE.chmod(0o600)
    return KEY_FILE


def probe_api_key(key: str) -> str:
    """Try the key against UTS with one uncached request. Returns '' when it
    works, else a message for the curator (never containing the key)."""
    try:
        UTSClient(key, cache_dir=None).get_concept("C0017337")  # Genes
    except Exception as ex:  # noqa: BLE001
        code = getattr(getattr(ex, "response", None), "status_code", None)
        if code in (401, 403):
            return (f"UTS rejected this key (HTTP {code}). Copy it again from "
                    f"your UTS profile ({UTS_PROFILE_URL}); a newly created "
                    "account is usable only after NLM approves the license.")
        return f"could not reach UTS: {type(ex).__name__}: {ex}"
    return ""


def no_key_help() -> str:
    """The API's answer to a UMLS request made without a key. Short on
    purpose: the browser opens the Connect UMLS walkthrough on needs_key, and
    the console prints the full steps at startup."""
    return ("UMLS is not connected: this needs a UMLS API key. Use Connect "
            f"UMLS in the Studio (free UTS account: {UTS_SIGNUP_URL}) or "
            "export UMLS_API_KEY before starting.")


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


def _inv_load() -> dict:
    """The workspace inventory document ({} if absent). Loaded round-trip with
    ruamel.yaml when available so writes preserve the file's comments and
    layout; plain PyYAML otherwise."""
    if not H.INVENTORY.is_file():
        return {}
    try:
        from ruamel.yaml import YAML
        return YAML(typ="rt").load(H.INVENTORY.read_text()) or {}
    except ImportError:
        return yaml.safe_load(H.INVENTORY.read_text()) or {}


def _inv_save(doc: dict) -> None:
    H.INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    try:
        from ruamel.yaml import YAML
        y = YAML(typ="rt")
        y.width = 100
        y.preserve_quotes = True
        with H.INVENTORY.open("w") as fh:
            y.dump(doc, fh)
    except ImportError:
        H.INVENTORY.write_text(
            yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100))


def _dimensions() -> dict:
    """The inventory's dimensions block (empty if the workspace has no inventory)."""
    return dict(_inv_load().get("dimensions") or {})


def _norm_sabs(x) -> list:
    """Normalise a preferred-SAB list given as a list or a comma/space string:
    upper-cased, stripped, de-duplicated, order kept."""
    if not x:
        return []
    items = x if isinstance(x, (list, tuple)) else re.split(r"[,\s]+", str(x))
    out = []
    for it in items:
        it = str(it).strip().upper()
        if it and it not in out:
            out.append(it)
    return out


def _rationale_view(a: dict) -> dict:
    """The recorded argument of one adjudication, in the shape the UI renders:
    relation (or None), rejected (always a list), protocol (always a dict)."""
    rej = a.get("rejected")
    proto = a.get("protocol")
    return {"relation": a.get("relation") or None,
            "rejected": list(rej) if isinstance(rej, list) else [],
            "protocol": dict(proto) if isinstance(proto, dict) else {}}


def entry_needs(e: dict, dim_has_values: bool = True) -> list:
    """The need codes (NEED_CODES) of one state entry -- the single place that
    says what still needs a curator's eyes. Empty list = nothing to do.

    value entries: unbuilt       in the inventory but absent from the crosswalk
                                 -- never queried
                   review        status review
                   unconfirmed   auto-mapped by the harness, never confirmed
                   unresolved    unmapped because the harness query returned
                                 nothing (or it was all filtered out) -- a gap,
                                 not a verdict
                   no-rationale  a curator's unmapped verdict carrying neither
                                 rejected candidates nor a protocol
    axis entries:  untyped       no semantic type while the dimension has values
                                 to search (boolean / free-text dimensions with
                                 no values are not flagged)"""
    if e.get("kind") == "axis":
        return ["untyped"] if dim_has_values and not e.get("sty_tui") else []
    status, curated = e.get("status"), bool(e.get("curated"))
    if status == "pending":
        # in the inventory, never resolved: the harness has not queried it (a
        # rebuild that failed or has not run). Not a verdict -- unfinished work.
        return ["unbuilt"]
    # The crosswalk snapshot only changes on Rebuild; the live adjudication
    # (entry["decision"]) wins so the flags follow decisions made in-session.
    dec = e.get("decision")
    if e.get("error"):                     # e.g. an accepted CUI the harness could not confirm
        return ["review"]
    if dec == "accept":
        status, curated = "mapped", True
    elif dec == "unmapped":
        status, curated = "unmapped", True
    elif "decision" in e and dec is None and curated:   # cleared since the last Rebuild
        curated = False
    if status == "review":
        return ["review"]
    if status == "mapped":
        return [] if curated else ["unconfirmed"]
    if status == "unmapped":
        if not curated:
            return ["unresolved"]
        if not e.get("rejected") and not e.get("protocol"):
            return ["no-rationale"]
    return []


def load_state() -> dict:
    """Assemble the UI state from whatever the workspace has. Axes come from the
    inventory (so they exist even before any crosswalk is built), values from the
    crosswalk when present. Every file is optional -- an empty workspace yields
    no dimensions, ready for the axis builder to create the first one."""
    inv_doc = _inv_load()
    dims = dict(inv_doc.get("dimensions") or {})
    ws_prefs = _norm_sabs((inv_doc.get("meta") or {}).get("preferred_sabs"))
    adj = H.load_adjudications(H.ADJUDICATIONS)
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

    # The INVENTORY is the source of truth for which values exist; the crosswalk
    # is a resolved snapshot of it. A value present in the former and missing
    # from the latter (just added, or a rebuild that failed) is shown as
    # 'pending' rather than not at all -- otherwise adding a value looks like
    # nothing happened, which is exactly the trap this workspace used to set.
    inv_values: dict = {}
    for dim, block in dims.items():
        for kind, seq in VALUE_SEQS.items():
            for v in (block or {}).get(seq) or []:
                if not isinstance(v, dict) or v.get("token") is None:
                    continue
                inv_values.setdefault(dim, {})[str(v["token"])] = (kind, dict(v))
    for dim, byname in inv_values.items():
        have = {str(e.get("token")) for e in values_by_dim.get(dim, [])}
        for tok, (kind, v) in byname.items():
            if tok in have:
                continue
            values_by_dim.setdefault(dim, []).append({
                "dimension": dim, "token": v["token"], "kind": kind,
                "query": v.get("query") or "", "status": "pending",
                "expect": v.get("expect"), "sab": v.get("sab"),
                "inventory_note": v.get("note"), "candidates": []})

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
        ax = {
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
            "preferred_sabs": _norm_sabs(block.get("preferred_sabs")),
            "dim_sty_tui": eff, "dim_sty_filter": filt,
            "decision": ("accept_sty" if aadj.get("accept_sty")
                         else "unmapped" if aadj.get("unmapped") else None),
            "decision_cui": None, "decision_sty": aadj.get("accept_sty"),
            "note": aadj.get("note"), "error": None,
            **_rationale_view(aadj),
        }
        ax["needs"] = entry_needs(ax, bool(values_by_dim.get(dim)))
        entries.append(ax)
        # value entries for this dimension (from the crosswalk)
        for e in values_by_dim.get(dim, []):
            key = H._adj_key(e["dimension"], e["token"])
            a = adj.get(key) or {}
            v = {
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
                "dim_sty_name": sty.get("name") if sty else None,
                "dim_sty_tree": sty.get("tree_number") if sty else None,
                "sab_pref": e.get("sab"),
                # effective preference order: the value's own hint, then the
                # dimension override, then the workspace list
                "sab_prefs": _norm_sabs(([e.get("sab")] if e.get("sab") else [])
                                        + _norm_sabs(block.get("preferred_sabs"))
                                        + ws_prefs),
                "decision": ("accept" if a.get("accept") else
                             "accept_sty" if a.get("accept_sty") else
                             "unmapped" if a.get("unmapped") else None),
                "decision_cui": a.get("accept"), "decision_sty": a.get("accept_sty"),
                "note": a.get("note"), "error": e.get("curator_error"),
                "search_type": e.get("search_type"),
                # the inventory definition behind this value, for the editor:
                # None/absent means the crosswalk carries a row the inventory
                # no longer defines (hand-edited or deleted elsewhere)
                "expect": e.get("expect"),
                "inventory_note": e.get("inventory_note"),
                "in_inventory": str(e["token"]) in (inv_values.get(e["dimension"]) or {}),
                **_rationale_view(a),
            }
            v["needs"] = entry_needs(v)
            entries.append(v)

    # Always computed over VALUE entries (never axes), so the Home progress
    # numbers mean what they say -- the crosswalk's meta.counts mixes axes in
    # and carries no total.
    vals = [e for e in entries if e["kind"] != "axis"]
    counts = {"total": len(vals),
              "mapped": sum(e["status"] == "mapped" for e in vals),
              "unmapped": sum(e["status"] == "unmapped" for e in vals),
              "review": sum(e["status"] == "review" for e in vals),
              "curated": sum(bool(e["curated"]) for e in vals)}
    # per-code totals over EVERY entry (axes included), in NEED_CODES order;
    # counts.needs is the number of entries with anything left to do
    needs = {c[0]: 0 for c in NEED_CODES}
    for e in entries:
        for c in e["needs"]:
            needs[c] += 1
    counts["needs"] = sum(1 for e in entries if e["needs"])
    return {"entries": entries, "counts": counts,
            "needs": needs, "need_codes": [c[0] for c in NEED_CODES],
            "need_labels": NEED_LABELS,
            "workspace": str(DATA_DIR), "dimensions": sorted(dims),
            "prefs": {"workspace": ws_prefs},
            "search_backend": SEARCH_BACKEND, "help_url": HELP_URL,
            "server": {"started": SERVER_STARTED, "code": CODE_STAMP},
            "search_backend_note": SEARCH_BACKEND_NOTE,
            # never the key itself -- only whether one is loaded and from where
            "umls": {"connected": UTS_ONLINE, "key_source": KEY_SOURCE,
                     "local_index": LOCAL_INDEX, "key_file": str(KEY_FILE),
                     "signup_url": UTS_SIGNUP_URL, "profile_url": UTS_PROFILE_URL}}


def write_adjudications(adj: dict) -> None:
    """Write adjudications.yaml. Entries that carry only a decision and a note
    stay one compact flow-style line each (as the file has always been);
    entries with a structured rationale (relation / rejected / protocol) are
    emitted as an indented block mapping so the argument stays readable. Both
    forms load back through H.load_adjudications() unchanged."""
    L = list(ADJ_HEADER) + ["adjudications:"]
    for key in sorted(adj):
        v = adj[key]
        if v.get("accept"):
            head = ("accept", v["accept"])
        elif v.get("accept_sty"):
            head = ("accept_sty", v["accept_sty"])
        elif v.get("unmapped"):
            head = ("unmapped", True)
        else:
            continue
        qkey = json.dumps(str(key), ensure_ascii=False)   # YAML double-quoted
        note = v.get("note") or ""
        rationale = {k: v[k] for k in RATIONALE_KEYS if v.get(k) is not None}
        if not rationale:
            hv = "true" if head[1] is True else head[1]
            L.append(f'  {qkey}: {{{head[0]}: {hv}, '
                     f'note: {json.dumps(note, ensure_ascii=False)}}}')
            continue
        entry = {head[0]: head[1], "note": note, **rationale}
        block = yaml.safe_dump(entry, sort_keys=False, allow_unicode=True,
                               width=100, default_flow_style=False)
        L.append(f"  {qkey}:")
        L.extend("    " + line for line in block.rstrip("\n").splitlines())
    H.ADJUDICATIONS.write_text("\n".join(L) + "\n")


def save_axis(dimension: str, semantic_type=None, query=None, note=None,
              tier=None, activation=None, order=None, preferred_sabs=None) -> dict:
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
    inv = _inv_load()
    block = inv.setdefault("dimensions", {}).setdefault(dimension, {})
    if tier:
        block["tier"] = tier
    if preferred_sabs is not None:          # [] clears the override
        lst = _norm_sabs(preferred_sabs)
        if lst:
            block["preferred_sabs"] = lst
        else:
            block.pop("preferred_sabs", None)
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
    _inv_save(inv)
    return dict(axis)


# ---- values ---------------------------------------------------------------
# A dimension's VALUES are the tokens adjudicated to concepts. They live in the
# inventory beside the axis (dimensions.<dim>.values, or common_values for the
# open dimensions whose tokens are conventions rather than schema enumerations),
# and until now could only be added by hand-editing the YAML -- so a workspace
# built from scratch through the UI could never acquire one. These are the
# inventory-side primitives behind /api/value.
def _find_value(block: dict, token) -> tuple:
    """(sequence name, index, entry) of one token in a dimension block, or
    (None, None, None). Both value sequences are searched: a token is unique
    within its dimension whichever list holds it."""
    for seq in VALUE_SEQS.values():
        for i, v in enumerate(block.get(seq) or []):
            if isinstance(v, dict) and str(v.get("token")) == str(token):
                return seq, i, v
    return None, None, None


def _new_value_entry(fields: dict):
    """A fresh inventory value. Emitted flow-style ({token: X, query: Y}) to
    match how the value lists have always been written."""
    try:
        from ruamel.yaml.comments import CommentedMap
        m = CommentedMap(fields)
        m.fa.set_flow_style()
        return m
    except ImportError:
        return dict(fields)


def save_value(dimension: str, token: str, query=None, expect=None, sab=None,
               note=None, kind: str = "value", old_token=None) -> dict:
    """Create or update one value of a dimension in the workspace inventory.

    ``old_token`` renames an existing value in place (keeping its position and
    surrounding comments) and carries its adjudication over to the new key, so a
    corrected token does not silently abandon the curator's decision. Returns
    the resulting inventory entry as a plain dict."""
    dimension = (dimension or "").strip()
    token = str(token or "").strip()
    old_token = str(old_token).strip() if old_token else None
    if kind not in VALUE_SEQS:
        raise ValueError(f"unknown value kind {kind!r}")
    if not dimension:
        raise ValueError("a dimension name is required")
    if not token:
        raise ValueError("a token is required")
    if not _TOKEN_RE.fullmatch(token):
        raise ValueError("token must be an identifier: letters, digits, "
                         "_ . : + - (no spaces)")
    query = _rs(query, "query")
    if not query:
        # The harness reads src["query"] unconditionally; a value without one
        # would break every rebuild of the dimension.
        raise ValueError("a query is required -- it is the term sent to UMLS")
    if expect and expect not in EXPECTS:
        raise ValueError(f"expect must be one of {', '.join(EXPECTS)}")
    sabs = _norm_sabs(sab)
    if len(sabs) > 1:
        raise ValueError("a value takes at most one source-vocabulary hint")

    inv = _inv_load()
    dims = inv.get("dimensions") or {}
    if dimension not in dims:
        raise ValueError(f"dimension {dimension!r} is not in the inventory")
    block = dims[dimension]
    # old_token is what makes this an UPDATE. Without it the call creates, and
    # an existing token is a collision -- never a silent overwrite of the
    # query, note and prior of a value somebody else defined.
    if old_token:
        _, _, existing = _find_value(block, old_token)
        if existing is None:
            raise ValueError(f"{old_token!r} is not a value of {dimension}")
        if token != old_token and _find_value(block, token)[2] is not None:
            raise ValueError(f"{dimension} already has a value {token!r}")
    else:
        existing = None
        if _find_value(block, token)[2] is not None:
            raise ValueError(f"{dimension} already has a value {token!r} — "
                             "edit that one instead of adding a second")

    fields = {"token": token, "query": query}
    if expect:
        fields["expect"] = expect
    if sabs:
        fields["sab"] = sabs[0]
    note = _rs(note, "note")
    if note:
        fields["note"] = note

    if existing is None:
        block.setdefault(VALUE_SEQS[kind], []).append(_new_value_entry(fields))
        entry = fields
    else:
        # Update in place so ruamel keeps the entry's position and comments.
        for k in ("token", "query", "expect", "sab", "note"):
            if k in fields:
                existing[k] = fields[k]
            else:
                existing.pop(k, None)
        entry = dict(existing)
    _inv_save(inv)

    if old_token and old_token != token:
        adj = H.load_adjudications(H.ADJUDICATIONS)
        prev = adj.pop(H._adj_key(dimension, old_token), None)
        if prev is not None:
            adj[H._adj_key(dimension, token)] = prev
            write_adjudications(adj)
    return entry


def delete_value(dimension: str, token: str) -> dict:
    """Remove one value from a dimension, together with any adjudication of it.

    The decision goes with the token deliberately: leaving it behind would make
    re-adding the same token resurrect a mapping the curator never re-made, and
    the Studio does not present decisions nobody took. Returns what was removed."""
    dimension = (dimension or "").strip()
    token = str(token or "").strip()
    inv = _inv_load()
    block = (inv.get("dimensions") or {}).get(dimension)
    if block is None:
        raise ValueError(f"dimension {dimension!r} is not in the inventory")
    seq, idx, existing = _find_value(block, token)
    if existing is None:
        raise ValueError(f"{token!r} is not a value of {dimension}")
    removed = dict(existing)
    del block[seq][idx]
    if not block[seq]:
        del block[seq]
    _inv_save(inv)

    adj = H.load_adjudications(H.ADJUDICATIONS)
    dropped = adj.pop(H._adj_key(dimension, token), None)
    if dropped is not None:
        write_adjudications(adj)
    return {"removed": removed, "dropped_adjudication": dropped is not None}


def rebuild_workspace(dim: str | None = None) -> dict:
    """Re-resolve the workspace against UMLS and rewrite the crosswalk snapshot.

    ``dim`` scopes the rebuild to one dimension, merged into the existing
    crosswalk in place (every other dimension is left exactly as it was);
    without it the whole inventory is rebuilt. Returns the written document."""
    if dim:
        part = H.build(client, live=True, only_dims={dim})
        if not part["entries"]:
            # dim not in the inventory (renamed/removed by hand?): merging an
            # empty part would only DELETE its existing crosswalk entries --
            # refuse instead of destroying data.
            raise ValueError(f"dimension {dim!r} is not in the inventory; "
                             "nothing to rebuild")
        doc = (yaml.safe_load(CROSSWALK.read_text())
               if CROSSWALK.is_file() else None)
        if doc and doc.get("entries"):
            merged, inserted = [], False
            for e in doc["entries"]:
                if e.get("dimension") == dim:
                    if not inserted:
                        merged.extend(part["entries"])
                        inserted = True
                    continue
                merged.append(e)
            if not inserted:
                merged.extend(part["entries"])
            doc["entries"] = merged
        else:
            doc = part
        counts = {s: 0 for s in ("mapped", "review", "unmapped", "pending")}
        for e in doc["entries"]:
            counts[e["status"]] += 1
        counts["curated"] = sum(1 for e in doc["entries"] if e.get("curated"))
        counts["axis_typed"] = sum(1 for e in doc["entries"] if e.get("sty_tui"))
        doc["meta"]["counts"] = counts
        doc["meta"]["total"] = len(doc["entries"])
    else:
        doc = H.build(client, live=True)
    CROSSWALK.write_text(yaml.safe_dump(doc, sort_keys=False,
                                        allow_unicode=True, width=100))
    return doc


def save_prefs(preferred_sabs) -> list:
    """Workspace-wide preferred vocabulary order (inventory meta.preferred_sabs)."""
    inv = _inv_load()
    lst = _norm_sabs(preferred_sabs)
    meta = inv.setdefault("meta", {})
    if lst:
        meta["preferred_sabs"] = lst
    else:
        meta.pop("preferred_sabs", None)
    _inv_save(inv)
    return lst


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

    # other meaningful relations, grouped by their (labeled) rela -- the
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


def descend_search(cli, sab: str, code: str, query: str,
                   depth: int = 2, breadth: int = 60, limit: int = 20) -> list:
    """Ontology-guided query expansion: when a direct search finds no faithful
    match, walk DOWN the is_a children of an anchor concept within one source
    vocabulary and rank every descendant's name against ``query``. BFS with a
    visited-set (source hierarchies can be diamonds), at most ``breadth`` nodes
    expanded and ``depth`` levels (each expansion is one cached UTS call).
    Returns [{code, name, sab, depth, score, parent}] best-first."""
    import difflib

    def score(name: str) -> float:
        a, b = (query or "").lower(), (name or "").lower()
        if not a or not b:
            return 0.0
        r = difflib.SequenceMatcher(None, a, b).ratio()
        ta, tb = set(re.findall(r"[a-z0-9]+", a)), set(re.findall(r"[a-z0-9]+", b))
        overlap = len(ta & tb) / len(ta) if ta else 0.0
        return round(0.6 * r + 0.4 * overlap, 4)

    seen, out, frontier, expanded = {code}, [], [(code, None, 0)], 0
    while frontier and expanded < breadth:
        cur, parent, d = frontier.pop(0)
        if d >= depth:
            continue
        expanded += 1
        try:
            kids = cli.source_children(sab, cur) or []
        except Exception:  # noqa: BLE001 -- a leaf/forbidden node ends the branch
            kids = []
        for k in kids:
            if k["code"] in seen:
                continue
            seen.add(k["code"])
            out.append({"code": k["code"], "name": k["name"], "sab": k["sab"],
                        "depth": d + 1, "score": score(k["name"]),
                        "parent": parent if d else None})
            frontier.append((k["code"], k["name"], d + 1))
    # Direct children are the answer to "what are the descendants?" -- they are
    # always kept (a query only orders them); deeper levels compete by score
    # for the remaining slots. Sorted children-first, best-scored within depth.
    d1 = sorted([x for x in out if x["depth"] == 1],
                key=lambda x: (-x["score"], x["name"] or ""))
    deeper = sorted([x for x in out if x["depth"] > 1],
                    key=lambda x: (-x["score"], x["depth"], x["name"] or ""))
    keep = d1[:max(limit, len(d1))] + deeper[:max(0, limit - len(d1))]
    return keep


EXPAND_MAJOR = ("SNOMEDCT_US", "MSH", "NCI", "GO", "HPO")


def expand_search(cli, query: str, stys: str | None = None,
                  per_word: int = 3, kids_per: int = 12,
                  max_variants: int = 40) -> dict:
    """Ontology-aware query expansion: for each content word of ``query``,
    find the concepts literally named by that word, take their is_a
    NEIGHBOURS (children and a few ancestors) from the source hierarchies,
    substitute the neighbor's name for the word, and re-search every
    variant. "model organism" -> organism's children (animal, plant, ...) ->
    "model animal" -> Animal Model. Results carry their provenance
    (word -> substituted term, and the variant searched)."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]+", query or "")
             if len(w) > 2]
    variants: list[tuple[str, str, str]] = []
    seen_var = {(query or "").lower()}
    # per-word budget: otherwise the first word's expansions starve the rest
    quota = max(8, max_variants // max(1, len(words)))
    for w in words:
        n_word = 0
        try:
            named = cli.search(w, search_type="exact", page_size=10)[:per_word]
        except Exception:  # noqa: BLE001
            named = []
        for c in named:
            codes: dict = {}
            try:
                for a in cli.atoms(c["cui"]):
                    if (a.get("sab") in EXPAND_MAJOR and a.get("code")
                            and a.get("code") != "NOCODE"
                            and (a.get("language") or "ENG") == "ENG"):
                        codes.setdefault(a["sab"], a["code"])
            except Exception:  # noqa: BLE001
                continue
            # hyponyms two levels down (animal is under organism via
            # Eukaryota in NCI); ancestors are deliberately NOT substituted --
            # they head straight for vocabulary roots and produce junk.
            per_sab: list = []
            for sab in [x for x in EXPAND_MAJOR if x in codes][:2]:
                lst: list = []
                try:
                    d1 = cli.source_children(sab, codes[sab])[:kids_per]
                    lst += d1
                    for k in d1[:6]:
                        lst += cli.source_children(sab, k["code"])[:6]
                except Exception:  # noqa: BLE001
                    pass
                if lst:
                    per_sab.append(lst)
            # interleave the vocabularies: one tree's verbose taxa (SNOMED's
            # "Kingdom Animalia") must not starve another's clean names
            # (NCI's "Animal") out of the per-word budget
            neigh = [n for tup in __import__("itertools").zip_longest(*per_sab)
                     for n in tup if n is not None]
            for n in neigh:
                nm = re.sub(r"\s*\([^)]*\)$", "", (n.get("name") or "")).strip()
                if not nm or len(nm.split()) > 3:
                    continue
                v = re.sub(rf"\b{re.escape(w)}\b", nm, query, flags=re.I)
                if v.lower() in seen_var or n_word >= quota:
                    continue
                seen_var.add(v.lower())
                variants.append((v, w, nm))
                n_word += 1
    variants = variants[:max_variants]
    results, seen_cui = [], set()
    for v, w, nm in variants:
        try:
            hits = cli.search(v, search_type="words", semantic_types=stys,
                              page_size=30)[:5]
        except Exception:  # noqa: BLE001
            hits = []
        for h in hits:
            if h["cui"] in seen_cui:
                continue
            seen_cui.add(h["cui"])
            results.append({**h, "via": f"{w} → {nm}", "variant": v})
    return {"n_variants": len(variants), "results": results[:30]}


client = None  # set in main()
SEARCH_BACKEND = "UTS"
UTS_ONLINE = False            # a working UTS key is loaded
KEY_SOURCE = ""               # where the key came from: env / .envrc / key file / dialog
LOCAL_INDEX = False           # the optional PostgreSQL index is serving search
# /api paths that need UTS. Without a key they return {"needs_key": true}
# instead of silently empty results; the local index, when loaded, still
# serves /api/search and /api/sabs on its own.
# Reads that go to UMLS, plus EVERY write: a workspace may be browsed without a
# key (tables, recorded decisions, the axis and value definitions already in the
# inventory), but nothing may be changed until UMLS is connected -- a decision or
# a new value that cannot be resolved against the Metathesaurus is not a mapping.
# /api/state and /api/umls-key stay open in every state, so the browser can
# render the workspace read-only and walk the curator through entering a key.
UTS_PATHS = {"/api/search", "/api/rollup", "/api/sabs", "/api/expand",
             "/api/descend", "/api/concept", "/api/rebuild",
             "/api/decide", "/api/axis", "/api/prefs",
             "/api/value", "/api/value/delete"}
LOCAL_ONLY_OK = {"/api/search", "/api/sabs"}


def uts_required(path: str) -> bool:
    if UTS_ONLINE or path not in UTS_PATHS:
        return False
    return not (LOCAL_INDEX and path in LOCAL_ONLY_OK)


def connect_uts(key: str, source: str) -> None:
    """Swap the live UTS client in (keeping a local-index hybrid if present)."""
    global client, UTS_ONLINE, KEY_SOURCE, SEARCH_BACKEND, SEARCH_BACKEND_NOTE
    live = UTSClient(key, cache_dir=H.CACHE_DIR)
    if isinstance(client, HybridClient):
        client._uts = live
    else:
        client = live
        SEARCH_BACKEND = "UTS"
    if SEARCH_BACKEND_NOTE.startswith("no UMLS_API_KEY"):
        SEARCH_BACKEND_NOTE = ""
    UTS_ONLINE, KEY_SOURCE = True, source
SEARCH_BACKEND_NOTE = ""      # why the local-index probe failed, when it did
import datetime as _dt
SERVER_STARTED = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
CODE_STAMP = _dt.datetime.fromtimestamp(
    Path(__file__).stat().st_mtime).strftime("%Y-%m-%d %H:%M")


class HybridClient:
    """Local-index search + UTS for everything else. search/atoms and the
    axis-subtree browse come from the PostgreSQL index (exact, normalized and
    trigram matching over the full release, no REST ranking cap); concept
    details, relations, definitions, rollups and the source registry stay on
    UTS. Attribute fallback delegates to the UTS client."""

    def __init__(self, pg, uts):
        self._pg, self._uts = pg, uts

    def search(self, *a, **k):
        return self._pg.search(*a, **k)

    def atoms(self, *a, **k):
        return self._pg.atoms(*a, **k)

    def concepts_by_tui(self, *a, **k):
        return self._pg.concepts_by_tui(*a, **k)

    def release(self):
        return self._pg.release()

    def sources(self):
        try:
            src = self._uts.sources()
        except Exception:  # noqa: BLE001
            src = []
        return src or self._pg.sources()

    def __getattr__(self, name):
        return getattr(self._uts, name)


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
            if uts_required(u.path):
                return self._send(200, json.dumps(
                    {"error": no_key_help(), "needs_key": True}))
            if u.path == "/api/state":
                return self._send(200, json.dumps(load_state()))
            if u.path == "/api/search":
                term = (q.get("string") or [""])[0]
                sab = (q.get("sabs") or [""])[0] or None
                stys = (q.get("stys") or [""])[0] or None
                stype = (q.get("stype") or [""])[0] or "words"
                # "partial" is our alias for words + partialSearch=true; the
                # rest pass through as UTS searchType values.
                partial = stype == "partial"
                res = client.search(term, search_type="words" if partial else stype,
                                    sabs=sab, semantic_types=stys, partial=partial)
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
            if u.path == "/api/sabs":
                # English vocabularies a concept has atoms in -- cheap (atoms
                # are cached), used to enrich search-result cards so the curator
                # sees membership without opening the evidence panel.
                cui = (q.get("cui") or [""])[0]
                sabs = sorted({a["sab"] for a in client.atoms(cui)
                               if a.get("sab") and (a.get("language") or "ENG") == "ENG"})
                return self._send(200, json.dumps({"sabs": sabs}))
            if u.path == "/api/sources":
                try:
                    src = [x for x in client.sources() if (x.get("language") or "ENG") == "ENG"]
                except Exception:  # noqa: BLE001 -- offline: fall back below
                    src = []
                if not src:
                    src = [{"sab": k, "name": v} for k, v in BUILTIN_SABS.items()]
                src.sort(key=lambda x: x["sab"])
                return self._send(200, json.dumps({"sources": src}))
            if u.path == "/api/expand":
                term = (q.get("q") or [""])[0]
                stys = (q.get("stys") or [""])[0] or None
                cap = 16 if SEARCH_BACKEND.startswith(("UTS", "OFFLINE")) else 40
                out = expand_search(client, term, stys, max_variants=cap)
                return self._send(200, json.dumps(out))
            if u.path == "/api/descend":
                cui = (q.get("cui") or [""])[0]
                want = (q.get("sab") or [""])[0] or None
                term = (q.get("q") or [""])[0]
                depth = min(int((q.get("depth") or ["2"])[0]), 3)
                # The hierarchy rarely lives in the vocabulary that named the
                # concept (MTH names have no tree): walk EVERY English source
                # the concept has an atom in, requested/major sources first.
                atoms = [a for a in client.atoms(cui)
                         if a.get("sab") and a.get("code")
                         and a.get("code") != "NOCODE"
                         and (a.get("language") or "ENG") == "ENG"]
                by_sab: dict = {}
                for a in sorted(atoms, key=lambda a: (a.get("tty") != "PT",)):
                    by_sab.setdefault(a["sab"], a["code"])
                if not by_sab:
                    return self._send(200, json.dumps({"error":
                        f"{cui} has no source atom to descend from"}))
                MAJOR = ("MSH", "NCI", "SNOMEDCT_US", "HPO", "GO", "LNC", "CSP")
                order = ([want] if want in by_sab else []) +                     [x for x in MAJOR if x in by_sab and x != want] +                     [x for x in sorted(by_sab) if x not in MAJOR and x != want]
                rows, anchors = [], []
                for sab in order[:6]:
                    got = descend_search(client, sab, by_sab[sab], term,
                                         depth=depth, breadth=40, limit=12)
                    if got:
                        anchors.append({"sab": sab, "code": by_sab[sab]})
                        rows.extend(got)
                rows.sort(key=lambda x: (x["depth"], -x["score"], x["name"] or ""))
                return self._send(200, json.dumps(
                    {"anchors": anchors, "matches": rows[:48]}))
            if u.path == "/api/axisbrowse":
                stys = (q.get("stys") or [""])[0]
                fn = getattr(client, "concepts_by_tui", None)
                if not callable(fn) or not stys:
                    return self._send(200, json.dumps({"error":
                        "Axis browse needs the optional local UMLS index. "
                        "Build it once from your own licensed UMLS release: "
                        "see data/umls/README.md, section 'Local UMLS index "
                        "(PostgreSQL)' — then restart the Studio."}))
                return self._send(200, json.dumps(
                    {"concepts": fn(stys, limit=3000)}))
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

    def _resolve_dim(self, dim) -> dict:
        """Re-resolve one dimension after an inventory edit, so the value the
        curator just wrote comes back with its candidates instead of waiting for
        a manual Rebuild. The write has already succeeded when this runs: a
        failure here is reported as rebuild_error alongside ok, never as a
        failed write."""
        dim = (dim or "").strip()
        try:
            doc = rebuild_workspace(dim or None)
            return {"counts": doc["meta"]["counts"]}
        except Exception as ex:  # noqa: BLE001 -- UMLS hiccup, not a lost edit
            return {"rebuild_error": f"{type(ex).__name__}: {ex}"}

    def do_POST(self):
        ln = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(ln) or b"{}")
            u = urlparse(self.path)
            if u.path == "/api/umls-key":
                # The key travels browser -> this local server only; it is
                # never echoed back, logged, or written anywhere but KEY_FILE.
                key = str(data.get("key") or "").strip()
                if not key:
                    return self._send(400, json.dumps({"error": "empty key"}))
                why = probe_api_key(key)
                if why:
                    return self._send(200, json.dumps({"error": why}))
                connect_uts(key, "dialog")
                out = {"ok": True, "key_source": KEY_SOURCE}
                if data.get("remember"):
                    try:
                        out["key_file"] = str(remember_api_key(key))
                        globals()["KEY_SOURCE"] = "key file"
                        out["key_source"] = "key file"
                    except OSError as ex:
                        out["remember_error"] = f"{type(ex).__name__}: {ex}"
                print(f"UMLS connected (key from {out['key_source']}).")
                return self._send(200, json.dumps(out))
            if uts_required(u.path):
                return self._send(200, json.dumps(
                    {"error": no_key_help(), "needs_key": True}))
            if u.path == "/api/decide":
                adj = H.load_adjudications(H.ADJUDICATIONS)
                key, verdict = data["key"], data.get("verdict")
                if verdict not in ("accept", "accept_sty", "unmapped", "clear"):
                    return self._send(400, json.dumps({"error": "bad verdict"}))
                try:
                    rationale = validate_rationale(verdict, data)
                    if verdict == "accept":
                        cui = _rs(data.get("cui"), "cui")
                        if not cui or not _ID_RE.fullmatch(cui):
                            raise ValueError("accept needs a CUI")
                        adj[key] = {"accept": cui,
                                    "note": data.get("note") or "curator-accepted via UI",
                                    **rationale}
                    elif verdict == "accept_sty":
                        adj[key] = {"accept_sty": data["tui"],
                                    "note": data.get("note") or "axis semantic type set via UI",
                                    **rationale}
                    elif verdict == "unmapped":
                        adj[key] = {"unmapped": True,
                                    "note": data.get("note") or "no faithful UMLS concept (curator)",
                                    **rationale}
                    else:                     # clear: decision AND rationale go
                        adj.pop(key, None)
                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                write_adjudications(adj)
                return self._send(200, json.dumps({"ok": True}))
            if u.path == "/api/axis":
                try:
                    axis = save_axis(data.get("dimension"),
                                     semantic_type=data.get("semantic_type") or None,
                                     query=data.get("query"), note=data.get("note"),
                                     tier=data.get("tier") or None,
                                     activation=data.get("activation"),
                                     order=data.get("order"),
                                     preferred_sabs=data.get("preferred_sabs"))
                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                # the inventory is now authoritative for this axis's type; drop a
                # stale accept_sty adjudication override so it takes effect.
                adj = H.load_adjudications(H.ADJUDICATIONS)
                akey = H._adj_key((data.get("dimension") or "").strip(), None)
                if (adj.get(akey) or {}).get("accept_sty"):
                    adj.pop(akey, None)
                    write_adjudications(adj)
                return self._send(200, json.dumps({"ok": True, "axis": axis}))
            if u.path == "/api/prefs":
                lst = save_prefs(data.get("preferred_sabs"))
                return self._send(200, json.dumps({"ok": True, "preferred_sabs": lst}))
            if u.path == "/api/rebuild":
                dim = (data.get("dim") or "").strip() or None
                try:
                    doc = rebuild_workspace(dim)
                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                return self._send(200, json.dumps({"ok": True, "dim": dim,
                                                   "counts": doc["meta"]["counts"]}))
            if u.path == "/api/value":
                try:
                    entry = save_value(data.get("dimension"), data.get("token"),
                                       query=data.get("query"),
                                       expect=data.get("expect") or None,
                                       sab=data.get("sab"),
                                       note=data.get("note"),
                                       kind=data.get("kind") or "value",
                                       old_token=data.get("old_token") or None)
                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                out = {"ok": True, "value": entry,
                       **self._resolve_dim(data.get("dimension"))}
                return self._send(200, json.dumps(out))
            if u.path == "/api/value/delete":
                try:
                    res = delete_value(data.get("dimension"), data.get("token"))
                except ValueError as ve:
                    return self._send(400, json.dumps({"error": str(ve)}))
                out = {"ok": True, **res,
                       **self._resolve_dim(data.get("dimension"))}
                return self._send(200, json.dumps(out))
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
#brand .txt{flex:1;min-width:0}
#gear{flex-shrink:0;width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:7px;color:var(--faint);cursor:pointer;border:1px solid transparent}
#gear:hover{color:var(--accent);background:#e9e5d8;border-color:var(--line)}
#help{flex-shrink:0;width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:7px;color:var(--faint);border:1px solid transparent;text-decoration:none}
#help:hover{color:var(--accent);background:#e9e5d8;border-color:var(--line)}
/* a control that would change the workspace, while UMLS is not connected */
button:disabled,button.blocked{opacity:.42;cursor:not-allowed}
.vt td.acts{text-align:right;white-space:nowrap;width:1%}
.vt td.acts button{visibility:hidden}
.vt tr.vrow:hover td.acts button,.vt td.acts button:disabled{visibility:visible}
.vrow.pendingrow .tk{color:var(--faint)}
.vedit label{display:block;font-size:10.5px;font-weight:600;letter-spacing:.07em;color:var(--faint);margin:9px 0 3px}
.vedit input,.vedit select{width:100%;font:inherit;font-size:12.5px;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
.vedit .mono{font-family:var(--mono);font-size:12px}
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
.crumb{font-family:var(--mono);font-size:13px;font-weight:500;letter-spacing:.06em;color:#4c463a;text-transform:uppercase}
.crumb a{color:#4c463a}.crumb a:hover{color:var(--accent)}
.titlerow{display:flex;align-items:center;gap:12px;margin-top:4px;flex-wrap:wrap}
.title-serif{font-family:var(--serif);font-size:24px;font-weight:700}
.title-mono{font-family:var(--mono);font-size:21px;font-weight:500}
.titlerow .spacer{flex:1}
#msg{font-size:12px;color:var(--mut)}
.orient{margin-top:6px;font-size:13px;color:var(--mut);max-width:780px}
.keybanner{margin:12px 0 0;padding:9px 12px;border:1px solid var(--warn);border-radius:8px;background:rgba(190,120,20,.07);font-size:13px;display:flex;gap:10px;align-items:center}
.keybanner .spacer{flex:1}
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
.sab{font-family:var(--mono);font-size:10px;color:var(--faint);border:1px solid var(--un-bd);border-radius:999px;padding:0 5px;white-space:nowrap}
.sab.ok{color:var(--ok);border-color:var(--ok-bd);background:var(--ok-bg);font-weight:600}
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
/* modal (Semantic Network popups) */
#modal{position:fixed;inset:0;background:rgba(35,30,20,.45);display:flex;align-items:center;justify-content:center;z-index:50}
#modal .mbox{background:var(--card);border:1px solid var(--line);border-radius:12px;width:min(760px,92vw);max-height:82vh;display:flex;flex-direction:column;box-shadow:0 12px 40px rgba(35,30,20,.28)}
#modal .mhead{display:flex;align-items:center;gap:10px;padding:11px 16px;border-bottom:1px solid var(--hair);font-size:13px}
#modal .mbody{padding:12px 16px;overflow:auto;font-size:12.5px}
.tawrap{position:relative;flex:1;min-width:0;display:flex}
.tawrap input{width:100%}
.tadrop{position:absolute;left:0;right:0;top:100%;margin-top:3px;background:var(--card);border:1px solid var(--line);border-radius:8px;box-shadow:0 8px 24px rgba(35,30,20,.18);max-height:240px;overflow:auto;z-index:60}
.taitem{display:flex;gap:10px;align-items:baseline;padding:6px 10px;cursor:pointer;font-size:12.5px}
.taitem:hover,.taitem.sel{background:#e9e5d8}
.taitem .ab{font-family:var(--mono);font-weight:500;min-width:110px}
.taitem .nm{color:var(--mut);font-size:11.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.stnlink{font-family:var(--mono);font-size:11px;color:var(--link);cursor:pointer;text-decoration:none;border-bottom:1px dotted var(--link)}
.stnlink:hover{text-decoration:none;border-bottom-style:solid}
.vocab{display:inline-block;background:var(--link-bg);color:var(--link);border:1px solid #cfdce8;border-radius:4px;padding:0 4px;margin:1px;font-size:11px}
/* needs: what still needs a curator's eyes (server-defined codes) */
.chip.needc{color:var(--warn);background:#f7ecdd;border-color:#eddabb}
.nbadge{display:inline-block;font-family:var(--mono);font-size:10px;font-weight:600;line-height:15px;color:var(--warn);background:#f7ecdd;border:1px solid #eddabb;border-radius:999px;padding:0 6px;margin-right:6px}
.wlbar{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.wlbar input{margin-left:auto;width:190px;font-size:12px}
.fchip{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:500;border-radius:999px;padding:2px 10px;border:1px solid var(--line);color:var(--mut);cursor:pointer;user-select:none;background:var(--card)}
.fchip:hover{background:#f4f1e8}
.fchip b{font-family:var(--mono);font-weight:600}
.fchip.on{color:#f6f3ea;background:var(--accent);border-color:var(--accent)}
.fchip.zero{opacity:.55}
.wlrow{display:grid;grid-template-columns:minmax(220px,1fr) minmax(0,1fr) auto;align-items:center;column-gap:12px;padding:7px 0;border-top:1px solid var(--hair);cursor:pointer;font-size:12.5px}
.wlrow:hover{background:#f4f1e8;margin:0 -17px;padding-left:17px;padding-right:17px}
.wlrow .dn{font-family:var(--mono);font-size:12px;display:flex;align-items:center;gap:7px;min-width:0}
.wlrow .dn .tk{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wlrow .st{display:flex;align-items:center;gap:5px;justify-self:end;white-space:nowrap}
.notice{display:flex;align-items:center;gap:7px;margin-top:8px;padding:7px 10px;border-radius:7px;font-size:12.5px;color:var(--warn);background:#f7ecdd;border:1px solid #eddabb}
</style></head><body>
<div id="rail"></div>
<div id="main"><div id="head"></div><div id="content"><div class="empty">Loading workspace…</div></div></div>
<script>
let STATE=null,SEMTYPES=null,SEL=null,AXB=null;
let ROUTE={view:'home'};
let OPEN={};          // conditional-group open/closed, keyed by activation
let FILTER={dim:null,status:'all',text:''};
let WL={need:'all',text:''};   // Home worklist filter (need code or 'all', text)
// per-value, in-session record of the adjudication protocol: the searches run
// (SEARCHLOG) and every candidate card rendered (SEEN, cui -> concept) -- the
// raw material of a structured "no faithful concept" argument.
const SEARCHLOG={},SEEN={};
const RELATIONS=['exact','close','broader','narrower','related'];
const CRITERIA={
  A:"denotation — the concept denotes a different thing or relation than the GEM token (e.g. a measurand degree vs an epistemic degree)",
  B:"granularity — only a broader/narrower concept exists and the gap is not acceptable as a proxy",
  C:"set membership — cannot serve as a point of the token’s scale/enumeration (not disjoint from / ordered with its siblings)",
  D:"domain sense — right words, wrong domain or context (e.g. an IPSS-R risk category named ‘High’)"};
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
 plus:'<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1.5v9M1.5 6h9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
 gear:'<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="2.2" stroke="currentColor" stroke-width="1.4"/><path d="M8 1.6v1.8M8 12.6v1.8M1.6 8h1.8M12.6 8h1.8M3.5 3.5l1.3 1.3M11.2 11.2l1.3 1.3M3.5 12.5l1.3-1.3M11.2 4.8l1.3-1.3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
 help:'<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6.3" stroke="currentColor" stroke-width="1.4"/><path d="M6.2 6.1a1.85 1.85 0 1 1 2.2 2.06c-.4.09-.4.5-.4.84" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><circle cx="8" cy="11.4" r=".85" fill="currentColor"/></svg>',
 pencil:'<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M8.2 1.6 10.4 3.8 4.1 10.1 1.5 10.5l.4-2.6 6.3-6.3Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>',
 trash:'<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M1.8 3.2h8.4M4.6 3.2V2.1h2.8v1.1M2.9 3.2l.5 6.7h5.2l.5-6.7" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>'};
/* ---------- vocabulary helpers ---------- */
const TTY={AB:'abbreviation',ACR:'acronym',BN:'brand name',DN:'display name',
 EP:'print entry term (MeSH)',ET:'entry term',FN:'fully specified name',
 HG:'high-level group term (MedDRA)',HT:'hierarchical term',IN:'ingredient name (RxNorm)',
 LA:'LOINC answer',LLT:'lower-level term (MedDRA)',MH:'main heading (MeSH)',
 NM:'supplementary concept name (MeSH)',OAF:'obsolete active fully specified name',
 OAP:'obsolete active preferred term',OAS:'obsolete active synonym',
 OF:'obsolete fully specified name',OL:'non-current lower-level term (MedDRA)',
 OP:'obsolete preferred term',PEP:'preferred entry term (MeSH)',
 PN:'Metathesaurus preferred name',PT:'preferred term',PTGB:'British preferred term',
 RPT:'root preferred term',SCD:'semantic clinical drug (RxNorm)',SY:'synonym',
 SYGB:'British synonym',TQ:'topical qualifier',XQ:'alternate qualifier name'};
function ttyHTML(t){if(!t)return '';
  let base=t,pre='';
  if(t.startsWith('MTH_')){base=t.slice(4);pre='Metathesaurus ';}
  const d=TTY[base];
  return d?`<span class="mono">${esc(t)}</span> <span class="mut" style="font-size:10.5px">${esc(pre+d)}</span>`
    :`<span class="mono" title="term type — see the UMLS TTY reference">${esc(t)}</span>`;}
// Enrich candidate cards with the full English SAB membership (root_source is
// only the name's highest-precedence source -- MTH means the Metathesaurus
// itself -- so membership must come from the atoms). The dimension's preferred
// SAB (inventory `sab:` hint) is ticked when present, flagged when absent.
const SABCACHE={};
async function fetchSabs(cui){if(SABCACHE[cui])return SABCACHE[cui];
  try{const j=await (await fetch('/api/sabs?cui='+encodeURIComponent(cui))).json();SABCACHE[cui]=j.sabs||[];}
  catch(err){SABCACHE[cui]=[];}
  return SABCACHE[cui];}
// ONE display rule for a concept's source, used everywhere a SAB is shown:
// the first preferred vocabulary the concept is actually in (ticked), else all
// of them; the search's root_source only until membership is known.
function sabLabel(sabs,prefs,root){prefs=prefs||[];
  if(!sabs||!sabs.length)return root?`<span class="sab" title="root source of the preferred name; membership not loaded">${esc(root)}</span>`:'';
  const all=sabs.join(', ');
  const p=prefs.find(x=>sabs.includes(x));
  if(p)return `<span class="sab ok" title="preferred vocabulary · also in: ${esc(all)}">${esc(p)} ✓</span>`+
    (sabs.length>1?`<span class="mini"> +${sabs.length-1}</span>`:'');
  const shown=sabs.slice(0,5).join(', ');
  return `<span class="sab" title="${esc(all)}">${esc(shown)}${sabs.length>5?' +'+(sabs.length-5):''}</span>`+
    (prefs.length?`<span class="mini" style="color:var(--rev)"> not in preferred (${esc(prefs.join(' › '))})</span>`:'');}
// fill every .sabslot[data-cui] under root with the membership-aware label
async function enrichSlots(root){
  const slots=[...(root||document).querySelectorAll('.sabslot[data-cui]:not([data-done])')];
  slots.forEach(el=>el.setAttribute('data-done','1'));
  await Promise.all(slots.map(async el=>{
    const sabs=await fetchSabs(el.getAttribute('data-cui'));
    if(!el.isConnected||!sabs.length)return;
    const prefs=(el.getAttribute('data-prefs')||'').split(',').filter(Boolean);
    el.innerHTML=sabLabel(sabs,prefs,el.getAttribute('data-root'));}));}
// candidate cards: append the full membership list, preferred ones first + ticked
async function enrichSabs(root){const prefs=(SEL&&SEL.sab_prefs)||[];
  const cards=[...(root||document).querySelectorAll('.cand[data-cui]:not([data-sabs])')];
  cards.forEach(el=>el.setAttribute('data-sabs','1'));
  await Promise.all(cards.map(async el=>{
    const sabs=await fetchSabs(el.getAttribute('data-cui'));
    if(!sabs.length||!el.isConnected)return;
    const hit=prefs.filter(p=>sabs.includes(p)),rest=sabs.filter(x=>!hit.includes(x));
    const show=hit.map(x=>`<b style="color:var(--ok)">${esc(x)} ✓</b>`).concat(rest.slice(0,10).map(esc)).join(', ')
      +(rest.length>10?` +${rest.length-10} more`:'');
    const miss=prefs.length&&!hit.length?` <span style="color:var(--rev)">(not in preferred: ${esc(prefs.join(' › '))})</span>`:'';
    const box=el.querySelector('.sty');
    if(box)box.insertAdjacentHTML('beforeend',` <span class="mini">· in: ${show}${miss}</span>`);}));}
/* ---------- vocabulary typeahead (comma-separated SAB lists) ---------- */
let SOURCES=null,_srcReq=null;
function loadSources(){if(SOURCES)return Promise.resolve(SOURCES);
  if(!_srcReq)_srcReq=fetch('/api/sources').then(r=>r.json()).then(j=>{SOURCES=j.sources||[];return SOURCES;}).catch(()=>{SOURCES=[];return SOURCES;});
  return _srcReq;}
// Attach to an <input>: the token being typed (after the last comma) narrows a
// dropdown of vocabularies (abbreviation prefix first, then any substring of
// abbreviation or name). Enter/click completes the token; Enter with the
// dropdown closed falls through to onEnter (e.g. save).
function attachSabTypeahead(input,onEnter){if(!input||input.dataset.ta)return;input.dataset.ta='1';
  const wrap=document.createElement('div');wrap.className='tawrap';
  input.parentNode.insertBefore(wrap,input);wrap.appendChild(input);
  const drop=document.createElement('div');drop.className='tadrop';drop.style.display='none';wrap.appendChild(drop);
  let items=[],sel=-1;
  const token=()=>{const v=input.value,i=v.lastIndexOf(',');return v.slice(i+1).trim();};
  const close=()=>{drop.style.display='none';items=[];sel=-1;};
  const pick=i=>{const it=items[i];if(!it)return;const v=input.value,c=v.lastIndexOf(',');
    input.value=(c>=0?v.slice(0,c+1)+' ':'')+it.sab+', ';close();input.focus();};
  const render=()=>{if(!items.length){close();return;}
    drop.innerHTML=items.map((it,i)=>`<div class="taitem ${i===sel?'sel':''}" data-i="${i}"><span class="ab">${esc(it.sab)}</span><span class="nm">${esc(it.name||'')}</span></div>`).join('');
    drop.style.display='block';
    drop.querySelectorAll('.taitem').forEach(el=>{el.onmousedown=ev=>{ev.preventDefault();pick(+el.dataset.i);};});};
  const update=async()=>{const q=token().toUpperCase();if(!q){close();return;}
    const src=await loadSources();
    const chosen=new Set(input.value.toUpperCase().split(',').map(x=>x.trim()).filter(Boolean));
    const pre=src.filter(x=>x.sab.toUpperCase().startsWith(q)&&!chosen.has(x.sab.toUpperCase()));
    const sub=src.filter(x=>!pre.includes(x)&&!chosen.has(x.sab.toUpperCase())&&(x.sab+' '+(x.name||'')).toUpperCase().includes(q));
    items=pre.concat(sub).slice(0,9);sel=items.length?0:-1;render();};
  input.addEventListener('input',update);
  input.addEventListener('blur',()=>setTimeout(close,120));
  input.addEventListener('keydown',ev=>{
    const open=drop.style.display!=='none'&&items.length;
    if(ev.key==='ArrowDown'&&open){sel=(sel+1)%items.length;render();ev.preventDefault();}
    else if(ev.key==='ArrowUp'&&open){sel=(sel-1+items.length)%items.length;render();ev.preventDefault();}
    else if(ev.key==='Enter'){if(open){pick(sel<0?0:sel);ev.preventDefault();ev.stopPropagation();}else if(onEnter)onEnter();}
    else if(ev.key==='Escape'&&open){close();ev.preventDefault();ev.stopPropagation();}
    else if(ev.key==='Tab'&&open){pick(sel<0?0:sel);ev.preventDefault();}});}
/* ---------- modal + Semantic Network views ---------- */
/* ---------- write guard ----------
   A workspace may be browsed without a UMLS key; it may not be CHANGED without
   one. Every control that writes carries data-write and is disabled until UMLS
   is connected — including inside modals, which is why this runs on each render
   and on each modal. The Connect UMLS controls deliberately carry no data-write. */
const WRITE_BLOCKED_MSG='Connect UMLS to change the workspace — without a key the Studio is read-only';
function writesBlocked(){return umlsOff();}
function applyWriteGuard(){if(!writesBlocked())return;
  document.querySelectorAll('[data-write]').forEach(el=>{
    el.disabled=true;el.classList.add('blocked');el.title=WRITE_BLOCKED_MSG;});}
function showModal(titleHTML,bodyHTML){closeModal();
  const d=document.createElement('div');d.id='modal';
  d.innerHTML=`<div class="mbox"><div class="mhead"><b>${titleHTML}</b><span style="flex:1"></span>`+
    `<button class="mini" onclick="closeModal()">close</button></div><div class="mbody">${bodyHTML}</div></div>`;
  d.addEventListener('click',ev=>{if(ev.target===d)closeModal();});
  document.body.appendChild(d);applyWriteGuard();}
function closeModal(){const m=$('#modal');if(m)m.remove();}
document.addEventListener('keydown',ev=>{if(ev.key==='Escape')closeModal();});
function mostSpecificTui(names){if(!SEMTYPES)return null;const norm=s=>(s||'').toLowerCase();
  let best=null;(names||[]).forEach(nm=>{const t=SEMTYPES.find(x=>norm(x.name)===norm(nm));
    if(t&&t.tree&&(!best||t.tree.split('.').length>best.tree.split('.').length))best=t;});
  return best;}
function showAxisTree(){if(!SEL||!SEL.dim_sty_tui)return;
  loadSemTypes().then(()=>showModal('Axis type in the Semantic Network — '+esc(SEL.dim_sty_name||SEL.dim_sty_tui),
    `<div class="subtree" style="max-height:none;border:none;padding:0">${stnPlaceHTML(SEL.dim_sty_tui,true)}</div>`));}
function showCompare(tui,axisTui){loadSemTypes().then(()=>{
  const t=(SEMTYPES||[]).find(x=>x.tui===tui);
  showModal('Place in the Semantic Network — '+esc(t?t.name:tui),
    stnCompareHTML(tui,axisTui!==undefined?axisTui:(SEL&&SEL.dim_sty_tui)));});}
// The result type's position relative to the axis type: shared ancestors as one
// spine, then the branches fork (axis and result each labeled).
function stnCompareHTML(tui,axisTui){
  const find=x=>(SEMTYPES||[]).find(t=>t.tui===x);
  const t=find(tui);if(!t||!t.tree)return '<i>type not in the Semantic Network</i>';
  const nest=(nodes,mark,tail)=>{let h=tail||'';
    for(let i=nodes.length-1;i>=0;i--){const n=nodes[i];const last=i===nodes.length-1;
      const cls=last&&mark?' '+mark:'';
      const lab=last&&mark==='hl'?' <span class="mini">← this result</span>'
        :last&&mark==='ax'?' <span class="mini">← axis</span>':'';
      h=`<div class="stn-node${cls}"><span class="stn-tree">${esc(n.tree)}</span> ${esc(n.name)}${lab}`+
        (h?`<div class="stn-kids">${h}</div>`:'')+`</div>`;}
    return h;};
  const chainOf=x=>{const c=stnParents(x.tree).map(pt=>(SEMTYPES||[]).find(y=>y.tree===pt)).filter(Boolean);
    c.push(x);return c;};
  const ct=chainOf(t),a=axisTui?find(axisTui):null;
  if(!a||!a.tree)return `<div class="stn-tree">${nest(ct,'hl')}</div><div class="mini" style="margin-top:6px">no axis type to compare against</div>`;
  const ca=chainOf(a);
  let k=0;while(k<ct.length&&k<ca.length&&ct[k].tui===ca[k].tui)k++;
  if(k===ca.length&&k===ct.length)
    return `<div class="stn-tree">${nest(ca,'ax')}</div><div class="mini" style="margin-top:6px">this result's type IS the axis type</div>`;
  if(k===ca.length)   // result lies inside the axis subtree
    return `<div class="stn-tree">${nest(ca,'ax',nest(ct.slice(k),'hl'))}</div>`+
      `<div class="mini" style="margin-top:6px">inside the axis subtree — an in-scope mapping</div>`;
  if(k===ct.length)   // result is an ancestor of the axis type
    return `<div class="stn-tree">${nest(ct,'hl',nest(ca.slice(k),'ax'))}</div>`+
      `<div class="mini" style="margin-top:6px">broader than the axis — an ancestor of the axis type</div>`;
  const common=ct.slice(0,k);
  const branches=nest(ca.slice(k),'ax')+nest(ct.slice(k),'hl');
  const body=common.length?nest(common,null,branches):branches;
  const note=k===0?'no common ancestor — a different branch of the Semantic Network'
    :'branches diverge after <b>'+esc(common[common.length-1].name)+'</b>';
  return `<div class="stn-tree">${body}</div><div class="mini" style="margin-top:6px">${note}</div>`;}
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
      unmapped:vals.filter(v=>v.status==='unmapped').length,
      // items still needing a curator (server-defined entry.needs): values + the axis
      needs:vals.reduce((n,v)=>n+(v.needs||[]).length,0)+(e.needs||[]).length});});
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
/* ---------- needs / worklist ----------
   What still needs a curator's eyes is decided by the server: every entry
   carries entry.needs (a list of codes), STATE.needs holds the per-code totals
   and STATE.need_labels the labels. Nothing here re-derives the definition. */
function needLabel(code){return ((STATE&&STATE.need_labels)||{})[code]||{label:code,desc:'',scope:'value'};}
function needChips(e){return (e.needs||[]).map(n=>{const l=needLabel(n);
  return `<span class="chip needc" title="${esc(l.desc)}">${esc(l.label)}</span>`;}).join(' ');}
// worklist order = STATE.entries order: dimension order, each axis before its values
function worklist(){return (STATE.entries||[]).filter(e=>(e.needs||[]).length);}
function wlFiltered(){const t=WL.text.toLowerCase();
  return worklist().filter(e=>(WL.need==='all'||(e.needs||[]).includes(WL.need))&&
    (!t||(e.dimension+' '+(e.token==null?'axis':e.token)+' '+(e.matched_name||'')).toLowerCase().includes(t)));}
function openEntry(e){if(!e)return;if(e.kind==='axis')gotoDim(e.dimension);else gotoValue(e.key);}
// the next entry after fromKey (wrapping around) that still needs a curator, or null
function nextNeeding(fromKey,need){need=need||WL.need||'all';const es=STATE.entries||[],n=es.length;
  const i=es.findIndex(x=>x.key===fromKey);
  const ok=e=>(e.needs||[]).length&&(need==='all'||e.needs.includes(need));
  for(let k=1;k<=n;k++){const e=es[(i+k+n)%n];if(e.key!==fromKey&&ok(e))return e;}
  return need==='all'?null:nextNeeding(fromKey,'all');}   // filtered chain exhausted: fall back to any need
function nextBtn(fromKey){const nx=nextNeeding(fromKey);if(!nx)return '';
  const what=(nx.needs||[]).map(c=>needLabel(c).label).join(', ');
  return `<button id="btn-next" title="${esc(nx.dimension)} › ${esc(nx.token==null?'axis':String(nx.token))} — ${esc(what)}">Next needing review →</button>`;}
function wireNext(fromKey){const b=$('#btn-next');if(b)b.addEventListener('click',()=>openEntry(nextNeeding(fromKey)));}
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
    `<span class="fr">${d.needs?`<span class="nbadge" title="${d.needs} item${d.needs===1?'':'s'} still need${d.needs===1?'s':''} a curator">${d.needs}</span>`:''}${frac}</span></div>`;}
function renderRail(){const g=grouped();const box=$('#rail');
  let h=`<div id="brand" onclick="gotoHome()">${IC.logo}<div class="txt"><div class="nm">GEM Mapping Studio</div>`+
    `<div class="ws">${esc(shortWs())} · ${(STATE.counts||{}).total||0} values</div></div>`+
    `<div id="gear" title="Settings — preferred vocabularies" onclick="event.stopPropagation();openSettings()">${IC.gear}</div>`+
    `<a id="help" href="${esc((STATE.help_url)||'')}" target="_blank" rel="noopener" title="Usage guide — how the workspace, search ladder and decisions work" onclick="event.stopPropagation()">${IC.help}</a>`+
    `</div><div id="nav">`;
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
  h+=`</div><div id="railfoot"><button data-write onclick="newAxis()">${IC.plus} New dimension</button></div>`;
  box.innerHTML=h;}
function toggleGroup(act){const g=grouped();const grp=g.cond.find(x=>x.act===act);
  const open=OPEN[act]!==undefined?OPEN[act]:(grp&&grp.dims.some(d=>d.dim===activeDim()));
  OPEN[act]=!open;renderRail();}
function shortWs(){const w=STATE.workspace||'';const parts=w.split('/');return parts.slice(-2).join('/');}
/* ---------- render dispatch ---------- */
function render(){if(!STATE)return;renderRail();
  if(ROUTE.view==='home')renderHome();
  else if(ROUTE.view==='dim')renderDim();
  else if(ROUTE.view==='value')renderValue();
  applyWriteGuard();}
function head(crumbHTML,titleHTML,orient){$('#head').innerHTML=
  `<div class="crumb">${crumbHTML}</div><div class="titlerow">${titleHTML}</div>`+
  (orient?`<div class="orient">${orient}</div>`:'')+keyBannerHTML();}
function umlsOff(){return !!(STATE&&STATE.umls&&!STATE.umls.connected);}
function keyBannerHTML(){if(!umlsOff())return '';
  const u=STATE.umls||{};
  return `<div class="keybanner"><b>UMLS is not connected — this workspace is read-only.</b> <span>You can browse dimensions, values and recorded decisions; changing any of them needs a UMLS API key${u.local_index?' (the local index still serves plain search)':''}, because a mapping the Metathesaurus has not confirmed is not a mapping.</span><span class="spacer"></span><button class="primary" onclick="showKeyDialog()">Connect UMLS…</button></div>`;}
/* ---------- UMLS key walkthrough ----------
   Any /api response carrying needs_key opens this dialog, so a missing key is
   never a silent empty result. The key goes to the local server only. */
function installKeyGuard(){const orig=window.fetch;let open=false;
  window.fetch=async function(url,opts){const r=await orig.apply(this,arguments);
    try{if(typeof url==='string'&&url.startsWith('/api/')&&!url.startsWith('/api/umls-key')){
      const j=await r.clone().json();
      if(j&&j.needs_key&&!open){open=true;showKeyDialog(j.error);setTimeout(()=>{open=false;},500);}}}catch(e){}
    return r;};}
function showKeyDialog(reason){const u=(STATE&&STATE.umls)||{};
  showModal('Connect UMLS',
    (reason?`<div class="mini" style="color:var(--warn);margin-bottom:8px">${esc(reason)}</div>`:'')+
    `<div style="font-size:13px;line-height:1.45">The Studio searches the UMLS Metathesaurus through the NLM UTS API, which needs your own (free) API key. The key stays on this machine: the browser sends it to the local Studio server only, and the server never echoes it back.</div>`+
    `<ol style="font-size:13px;line-height:1.5;margin:10px 0 6px 18px;padding:0">`+
    `<li>Create a UTS account and request the UMLS license: <a href="${esc(u.signup_url||'https://uts.nlm.nih.gov/uts/signup-login')}" target="_blank" rel="noopener">uts.nlm.nih.gov/uts/signup-login</a>. NLM reviews the request, usually within a few business days; the key does not work before approval.</li>`+
    `<li>Once approved, sign in and open your profile: <a href="${esc(u.profile_url||'https://uts.nlm.nih.gov/uts/profile')}" target="_blank" rel="noopener">uts.nlm.nih.gov/uts/profile</a>. Copy the <b>API key</b> shown there (generate one if the field is empty).</li>`+
    `<li>Paste it below and press <b>Test &amp; connect</b>. The Studio makes one test request before accepting it.</li></ol>`+
    `<div style="display:flex;gap:8px;margin-top:8px"><input id="umlskey" type="password" placeholder="UMLS API key" autocomplete="off" spellcheck="false" style="flex:1;font-family:var(--mono);font-size:12.5px">`+
    `<button class="primary" onclick="connectUmls()">Test &amp; connect</button></div>`+
    `<label class="mini" style="display:block;margin-top:8px"><input type="checkbox" id="umlsremember" checked> Remember on this machine (<span class="mono">${esc(u.key_file||'~/.config/forome-gem/umls_api_key')}</span>, readable by you only)</label>`+
    `<div id="umlskeymsg" class="mini" style="margin-top:8px"></div>`+
    `<div class="mini" style="margin-top:12px;color:var(--faint)">Alternatives: <span class="mono">export UMLS_API_KEY=…</span> before starting the Studio, or a repository <span class="mono">.envrc</span> under direnv. To forget a remembered key, delete the file above.</div>`);
  const i=$('#umlskey');if(i){i.focus();i.addEventListener('keydown',ev=>{if(ev.key==='Enter')connectUmls();});}}
async function connectUmls(){const key=(($('#umlskey')||{}).value||'').trim(),m=$('#umlskeymsg');
  if(!key){if(m)m.textContent='paste the key first';return;}
  if(m)m.textContent='testing the key against UTS…';
  let j;try{j=await (await fetch('/api/umls-key',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({key,remember:!!(($('#umlsremember')||{}).checked)})})).json();}
  catch(e){if(m)m.textContent='request failed: '+e;return;}
  if(j.error){if(m){m.style.color='var(--danger)';m.textContent=j.error;}return;}
  closeModal();await loadState();
  msg('UMLS connected'+(j.key_file?' — key remembered in '+j.key_file:'')+(j.remember_error?' (could not remember it: '+j.remember_error+')':''));}
/* ---------- HOME ---------- */
function renderHome(){const c=STATE.counts||{},g=grouped(),dims=dimList();
  head('WORKSPACE',
    `<span class="title-serif">Mapping workspace</span><span class="spacer"></span><span id="msg"></span>`+
    `<button data-write onclick="rebuild()" title="Re-queries UMLS for every dimension and value in the workspace and rewrites umls_crosswalk.yaml">Rebuild all</button><button class="primary" data-write onclick="newAxis()">New dimension</button>`,
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
     `<span><span class="ldot" style="background:var(--warn)"></span><b>${c.needs||0}</b> item${(c.needs||0)===1?'':'s'} need${(c.needs||0)===1?'s':''} review</span>`+
     `<span style="margin-left:auto" class="mono mini">${tot} values · ${dims.length} dimensions · ${c.curated||0} curated</span></div></div>`;
  h+=worklistCard();
  const rowHTML=d=>{const axis=d.tui?
      `<span class="chip tui">${esc(d.styTree||d.tui)}</span> <span>${esc(d.styName||'')}</span>`:
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
  $('#content').innerHTML=h;wireWorklist();}
/* ---------- HOME: worklist card ---------- */
function worklistCard(){const wl=worklist(),nc=STATE.needs||{};
  const chip=(code,label,n,desc)=>`<span class="fchip ${WL.need===code?'on':''} ${n?'':'zero'}" data-need="${esc(code)}" title="${esc(desc)}">${esc(label)} <b>${n}</b></span>`;
  return `<div class="card" id="wlcard"><h3>Worklist · ${wl.length}<span class="hint">what still needs a curator's eyes — every dimension, in dimension order</span></h3>`+
    `<div class="wlbar">`+chip('all','all',wl.length,'everything that still needs a curator')+
    (STATE.need_codes||[]).map(c=>chip(c,needLabel(c).label,nc[c]||0,needLabel(c).desc)).join('')+
    `<input id="wltext" placeholder="filter dimension / token…" value="${esc(WL.text)}">`+
    `<button class="primary" id="wlstart" title="open the first item of the current filter">Start review</button></div>`+
    `<div id="wllist" style="max-height:300px;overflow:auto">${wlRows()}</div></div>`;}
function wlRows(){const rows=wlFiltered();
  if(!rows.length)return `<div class="mini" style="padding:8px 0;font-style:italic">${worklist().length?'nothing matches the filter':'nothing needs review — every value is confirmed or argued, every axis typed'}</div>`;
  return rows.map(e=>`<div class="wlrow" data-key="${esc(e.key)}">`+
    `<div class="dn"><span class="dot ${esc(e.status)}"></span><span class="mut">${esc(e.dimension)} ›</span>`+
    `<span class="tk">${e.kind==='axis'?'<i>axis</i>':esc(String(e.token))}</span>`+
    (e.kind!=='axis'&&e.kind!=='value'?`<span class="condchip">${esc(e.kind)}</span>`:'')+`</div>`+
    `<div class="mut" style="font-size:12px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">`+
    (e.cui?esc(e.matched_name||'')+' <span class="cui">'+esc(e.cui)+'</span>':(e.kind==='axis'&&e.sty_name?esc(e.sty_name):''))+`</div>`+
    `<div class="st">${needChips(e)}<span class="chip st-${esc(e.status)}">${esc(e.status)}</span></div></div>`).join('');}
function wireWorklist(){const card=$('#wlcard');if(!card)return;
  const list=$('#wllist');
  card.querySelectorAll('.fchip').forEach(el=>el.addEventListener('click',()=>{const n=el.dataset.need;
    WL.need=(n==='all'||WL.need===n)?'all':n;   // single-select; clicking the active chip returns to all
    card.querySelectorAll('.fchip').forEach(x=>x.classList.toggle('on',x.dataset.need===WL.need));
    list.innerHTML=wlRows();}));
  const t=$('#wltext');if(t)t.addEventListener('input',()=>{WL.text=t.value;list.innerHTML=wlRows();});
  list.addEventListener('click',ev=>{const row=ev.target.closest('.wlrow');if(!row)return;
    openEntry(STATE.entries.find(x=>x.key===row.dataset.key));});
  $('#wlstart').addEventListener('click',()=>{const first=wlFiltered()[0];
    if(first)openEntry(first);else msg('nothing to review in this filter');});}
/* ---------- DIMENSION view ---------- */
function renderDim(){const isnew=!!ROUTE.isnew;
  const d=isnew?null:dimList().find(x=>x.dim===ROUTE.dim);
  if(!isnew&&!d){gotoHome();return;}
  const e=d?d.e:null;
  if(!AXB)AXB=e?{dimension:e.dimension,query:e.axis_query||'',note:e.axis_note||'',tui:e.sty_tui||null,
                 isnew:!e.in_inventory,tier:e.tier||'core',activation:e.activation||'',
                 prefs:(e.preferred_sabs||[]).join(', ')}
              :{dimension:'',query:'',note:'',tui:null,isnew:true,tier:'core',activation:'',prefs:''};
  const tierchip=`<span class="chip tier">${esc((AXB.tier||'core').toUpperCase())}</span>`;
  head(`<a href="#" onclick="gotoHome();return false">WORKSPACE</a> › ${esc((AXB.dimension||'NEW').toUpperCase())}`,
    `<span class="title-mono">${esc(AXB.dimension||'new dimension')}</span>${tierchip}`+
    (AXB.activation?`<span class="mini mono">${esc(AXB.activation)}</span>`:'')+
    (e?needChips(e):'')+
    `<span class="spacer"></span><span id="msg"></span>`+(e?nextBtn(e.key):'')+
    (AXB.isnew?'':`<button data-write onclick="rebuild('${jsq(AXB.dimension)}')" title="Re-queries UMLS for this dimension's values only; the rest of the crosswalk is untouched">Rebuild this dimension</button>`)+
    `<button class="primary" data-write onclick="axbSave()">${AXB.isnew?'Create axis':'Save axis'}</button>`,
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
      `<div class="axrow"><label>preferred</label><input id="axprefs" value="${esc(AXB.prefs||'')}" style="font-family:var(--mono);font-size:12px" placeholder="vocabularies for this dimension, e.g. HPO, MSH — blank inherits workspace${((STATE.prefs||{}).workspace||[]).length?' ('+esc(STATE.prefs.workspace.join(', '))+')':''}"></div>`+
      `<div class="mini" style="margin-left:82px">Run query surfaces the semantic <i>types</i> of matching concepts — an axis maps to a type, not a concept.</div>`+
    `</div></div>`+
    `<div id="axprev" style="margin-top:10px"></div>`+
    `<details style="margin-top:8px"><summary class="mini" style="cursor:pointer">Browse all 127 semantic types</summary>`+
    `<div class="searchbar" style="margin-top:8px"><input id="styq" placeholder="filter by name / TUI / tree…"></div>`+
    `<div id="styresults" class="stylist"></div></details></div>`;
  if(e){const vals=STATE.entries.filter(x=>x.dimension===e.dimension&&x.kind!=='axis');
    h+=`<div class="card"><h3>Values · ${vals.length}`+
      `<span class="hint">${d.mapped} mapped · ${d.review} in review · ${d.unmapped} unmapped · ${d.needs} need${d.needs===1?'s':''} review</span></h3>`+
      `<div style="display:flex;gap:8px;margin-bottom:6px">`+
      `<select id="fstatus" onchange="setFilter()" style="font-size:12px">`+
        `<option value="all">All</option><option value="needs">Needs attention (any)</option>`+
        (STATE.need_codes||[]).filter(c=>needLabel(c).scope!=='axis').map(c=>
          `<option value="need:${esc(c)}" title="${esc(needLabel(c).desc)}">needs: ${esc(needLabel(c).label)}</option>`).join('')+
        `<option value="mapped">Mapped</option>`+
        `<option value="unmapped">Unmapped</option><option value="curated">Curated</option><option value="auto">Auto (not curated)</option></select>`+
      `<input id="ftext" oninput="setFilter()" placeholder="filter token…" style="width:180px;font-size:12px">`+
      `<span class="spacer" style="flex:1"></span>`+
      `<button class="primary" data-write onclick="valueEditor('${jsq(e.dimension)}',null)" title="Define a new value of this dimension in the workspace inventory and resolve it against UMLS">${IC.plus} Add value</button>`+
      `</div><div id="vtbox">${valuesTable(vals)}</div></div>`;
    if(!vals.length)h+=`<div class="mini" style="margin:-6px 0 12px 4px">This dimension has no values yet. <b>Add value</b> writes one to the workspace inventory — a token and the term to search UMLS for — and resolves it within the axis type straight away. (<b>Rebuild</b> re-resolves the values the inventory already defines; it does not invent any.)</div>`;}
  $('#content').innerHTML=h;
  if(e)wireNext(e.key);
  if(AXB.isnew){['axdim','axtier','axact'].forEach(id=>{const el=$('#'+id);if(el)el.addEventListener('input',()=>{
      AXB.dimension=($('#axdim')||{}).value||'';AXB.tier=($('#axtier')||{}).value||'core';AXB.activation=($('#axact')||{}).value||'';});});
    const t=$('#axtier');if(t)t.addEventListener('change',()=>{AXB.tier=t.value;});}
  ['axq','axnote','axprefs'].forEach(id=>{const el=$('#'+id);if(el)el.addEventListener('input',()=>{
      AXB.query=($('#axq')||{}).value||'';AXB.note=($('#axnote')||{}).value||'';AXB.prefs=($('#axprefs')||{}).value||'';});});
  const q=$('#axq');if(q)q.addEventListener('keydown',ev=>{if(ev.key==='Enter')axbRun();});
  const sq=$('#styq');if(sq)sq.addEventListener('input',axbPicker);
  attachSabTypeahead($('#axprefs'));
  const fs=$('#fstatus');if(fs)fs.value=FILTER.status;const ft=$('#ftext');if(ft)ft.value=FILTER.text;
  enrichSlots($('#vtbox'));
  loadSemTypes().then(()=>{axbPicker();axbRenderSel();
    if(ROUTE.view==='dim'&&!ROUTE.isnew&&$('#vtbox'))setFilter();});}
function setFilter(){FILTER.dim=ROUTE.dim;FILTER.status=($('#fstatus')||{}).value||'all';FILTER.text=($('#ftext')||{}).value||'';
  const e=dimList().find(x=>x.dim===ROUTE.dim);if(!e)return;
  const vals=STATE.entries.filter(x=>x.dimension===ROUTE.dim&&x.kind!=='axis');
  $('#vtbox').innerHTML=valuesTable(vals);enrichSlots($('#vtbox'));applyWriteGuard();}
function passFilter(e){const f=FILTER.status,t=FILTER.text.toLowerCase();
  if(t&&!(String(e.token||'')+' '+e.dimension).toLowerCase().includes(t))return false;
  if(f==='all')return true;if(f==='mapped')return e.status==='mapped';if(f==='unmapped')return e.status==='unmapped';
  if(f==='curated')return e.curated;if(f==='auto')return e.status==='mapped'&&!e.curated;
  if(f==='needs')return (e.needs||[]).length>0;               // server-defined
  if(f.startsWith('need:'))return (e.needs||[]).includes(f.slice(5));return true;}
function valuesTable(vals){const rows=vals.filter(passFilter).map(e=>{
    const map=e.cui?`<span>${esc(e.matched_name||'')}</span> <span class="cui">${esc(e.cui)}</span> `+
      `<span class="sabslot" data-cui="${esc(e.cui)}" data-root="${esc(e.root_source||'')}" data-prefs="${esc((e.sab_prefs||[]).join(','))}">`+
      (e.root_source?`<span class="sab">${esc(e.root_source)}</span>`:'')+`</span>`:'<span class="mut">—</span>';
    const inv=e.in_inventory!==false;
    const noinv='not defined in the workspace inventory — the crosswalk carries a row the inventory does not';
    return `<tr class="vrow${e.status==='pending'?' pendingrow':''}" onclick="gotoValue('${jsq(e.key)}')">`+
      `<td style="width:16px"><span class="dot ${esc(e.status)}" style="display:inline-block"></span></td>`+
      `<td class="tk">${esc(e.token)}${e.kind!=='value'?` <span class="condchip">${esc(e.kind)}</span>`:''}</td>`+
      `<td class="mut">${esc(e.query)}</td><td>${map}</td><td>${styCell(e)}</td>`+
      `<td style="text-align:right;white-space:nowrap">${needChips(e)}${(e.needs||[]).length?' ':''}<span class="chip st-${esc(e.status)}">${esc(e.status)}</span>`+
      (e.curated?' <span class="badge">curated</span>':'')+`</td>`+
      `<td class="acts">`+
        `<button class="mini" data-write${inv?'':' disabled'} title="${inv?'edit this value&rsquo;s inventory definition':esc(noinv)}" onclick="event.stopPropagation();valueEditor('${jsq(e.dimension)}','${jsq(e.token)}')">${IC.pencil}</button> `+
        `<button class="mini" data-write${inv?'':' disabled'} title="${inv?'remove this value from the dimension':esc(noinv)}" onclick="event.stopPropagation();confirmDeleteValue('${jsq(e.dimension)}','${jsq(e.token)}')">${IC.trash}</button>`+
      `</td></tr>`;}).join('');
  return rows?`<table class="vt"><tr><th></th><th>TOKEN</th><th>QUERY</th><th>MAPPING</th><th>STY</th><th style="text-align:right">STATUS</th><th></th></tr>${rows}</table>`
    :'<div class="mini" style="padding:8px 0">no values match the filter</div>';}
// the mapped concept's most specific semantic type as STN + name (no TUI),
// clickable: its place in the network relative to the dimension's axis type
function styCell(e){if(!e.cui||!(e.semantic_types||[]).length)return '<span class="mut">—</span>';
  const st=mostSpecificTui(e.semantic_types);
  if(!st)return `<span class="mini">${esc(e.semantic_types.join(', '))}</span>`;
  return `<a href="#" class="stnlink" title="${esc(st.name)} — click to see its place relative to the axis type" `+
    `onclick="event.stopPropagation();showCompare('${st.tui}','${jsq(e.dim_sty_tui||'')}');return false">${esc(st.tree)}</a> `+
    `<span style="font-size:11.5px">${esc(st.name)}</span>`;}
/* ---------- values: the inventory definitions behind the table ----------
   A value is a token of the dimension plus the term the harness searches UMLS
   for. It lives in the workspace inventory next to the axis; saving one
   re-resolves the dimension so the token comes back with its candidates. */
function valueEditor(dim,token){
  const cur=token!=null?(STATE.entries||[]).find(x=>x.dimension===dim&&String(x.token)===String(token)):null;
  const v={token:cur?String(cur.token):'',query:cur?(cur.query||''):'',
           expect:(cur&&cur.expect)||'uncertain',sab:(cur&&cur.sab_pref)||'',
           note:(cur&&cur.inventory_note)||'',kind:(cur&&cur.kind)||'value'};
  const opts=(sel,list)=>list.map(x=>`<option${x===sel?' selected':''}>${x}</option>`).join('');
  showModal((cur?'Edit value · ':'New value · ')+`<span class="mono">${esc(dim)}</span>`,
    `<div class="vedit">`+
    `<div class="mini">Written to the workspace inventory, then resolved against this dimension&rsquo;s axis type. The harness records whatever it actually finds — never a concept you merely name.</div>`+
    `<label>token</label><input id="vtoken" class="mono" value="${esc(v.token)}" placeholder="e.g. HUMAN_GENETICS">`+
    `<label>query — the term sent to UMLS</label><input id="vquery" value="${esc(v.query)}" placeholder="e.g. Human genetics">`+
    `<label>expect — your honest prior that a faithful concept exists</label><select id="vexpect">${opts(v.expect,['likely','uncertain','unlikely'])}</select>`+
    `<label>preferred source vocabulary (optional)</label><input id="vsab" class="mono" value="${esc(v.sab)}" placeholder="e.g. MSH — blank searches every source">`+
    `<label>note (optional)</label><input id="vnote" value="${esc(v.note)}" placeholder="what the token means, or why the query is worded this way">`+
    (cur?`<div class="mini" style="margin-top:9px">Kind: <span class="mono">${esc(v.kind)}</span>. Renaming the token carries its recorded decision over to the new name.</div>`
        :`<label>kind</label><select id="vkind"><option value="value">value — a schema-enumerated token</option>`+
         `<option value="common_value">common_value — a convention on an open dimension</option></select>`)+
    `<div style="display:flex;align-items:center;gap:10px;margin-top:14px">`+
    `<button class="primary" data-write id="vsave">${cur?'Save value':'Add value'}</button>`+
    `<button onclick="closeModal()">Cancel</button><span id="vmsg" class="mini"></span></div></div>`);
  attachSabTypeahead($('#vsab'));
  const go=()=>saveValue(dim,token!=null?String(token):null);
  const b=$('#vsave');if(b)b.addEventListener('click',go);
  ['vtoken','vquery','vsab','vnote'].forEach(id=>{const el=$('#'+id);
    if(el)el.addEventListener('keydown',ev=>{if(ev.key==='Enter')go();});});
  const t=$('#vtoken');if(t){t.focus();t.select();}}
async function saveValue(dim,oldToken){
  const m=$('#vmsg'),body={dimension:dim,token:(($('#vtoken')||{}).value||'').trim(),
    query:($('#vquery')||{}).value||'',expect:($('#vexpect')||{}).value||'',
    sab:($('#vsab')||{}).value||'',note:($('#vnote')||{}).value||'',
    kind:($('#vkind')||{}).value||'value'};
  if(oldToken)body.old_token=oldToken;
  if(m){m.style.color='var(--faint)';m.textContent='saving, then querying UMLS…';}
  let j;try{j=await (await fetch('/api/value',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)})).json();}
  catch(err){if(m){m.style.color='var(--danger)';m.textContent='request failed: '+err;}return;}
  if(j.error){if(m){m.style.color='var(--danger)';m.textContent=j.error;}return;}
  closeModal();await loadState();
  msg(j.rebuild_error?`${body.token} saved — the rebuild failed: ${j.rebuild_error}`
                     :`${body.token} saved and resolved`);}
function confirmDeleteValue(dim,token){
  const cur=(STATE.entries||[]).find(x=>x.dimension===dim&&String(x.token)===String(token))||{};
  showModal('Delete value · '+`<span class="mono">${esc(token)}</span>`,
    `<div style="font-size:13px;line-height:1.45">Remove <b class="mono">${esc(token)}</b> from <b class="mono">${esc(dim)}</b> — out of the workspace inventory, and out of the crosswalk on the rebuild that follows.</div>`+
    (cur.decision?`<div class="mini" style="margin-top:9px;color:var(--warn)">Its recorded decision goes with it. Leaving the decision behind would resurrect a mapping you never re-made if the token were ever added again.</div>`:'')+
    `<div style="display:flex;align-items:center;gap:10px;margin-top:14px">`+
    `<button class="warn" data-write id="vdel">Delete value</button>`+
    `<button onclick="closeModal()">Cancel</button><span id="vmsg" class="mini"></span></div>`);
  const b=$('#vdel');if(b)b.addEventListener('click',()=>deleteValue(dim,token));}
async function deleteValue(dim,token){const m=$('#vmsg');
  if(m){m.style.color='var(--faint)';m.textContent='removing…';}
  let j;try{j=await (await fetch('/api/value/delete',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({dimension:dim,token})})).json();}
  catch(err){if(m){m.style.color='var(--danger)';m.textContent='request failed: '+err;}return;}
  if(j.error){if(m){m.style.color='var(--danger)';m.textContent=j.error;}return;}
  closeModal();
  // the deleted entry is still in STATE and may be the page we are on
  if(ROUTE.view==='value'){ROUTE={view:'dim',dim};SEL=null;AXB=null;}
  await loadState();
  msg(`${token} removed`+(j.dropped_adjudication?' (its decision too)':'')
      +(j.rebuild_error?` — the rebuild failed: ${j.rebuild_error}`:''));}
/* ---------- axis builder internals ---------- */
async function axbRun(){const q=(($('#axq')||{}).value||'').trim();const box=$('#axprev');if(!box)return;
  if(!q){box.innerHTML='<span class="mini">enter a query first</span>';return;}
  box.innerHTML='<span class="mini">searching UMLS…</span>';
  const j=await (await fetch('/api/search?string='+encodeURIComponent(q))).json();
  if(j.error){box.innerHTML='<span style="color:var(--danger)">'+esc(j.error)+'</span>';return;}
  const res=(j.results||[]).slice(0,60);
  if(!res.length){box.innerHTML='<span class="mini">no match. You can still pick a type below.</span>';return;}
  const norm=s=>(s||'').toLowerCase(),byT={};
  res.forEach(c=>(c.semantic_types||[]).forEach(nm=>{
    const t=(SEMTYPES||[]).find(x=>norm(x.name)===norm(nm));if(!t)return;
    const g=byT[t.tui]||(byT[t.tui]={tui:t.tui,name:t.name,tree:t.tree,n:0,ex:[]});
    g.n++;if(g.ex.length<5)g.ex.push(c.name);}));
  const types=Object.values(byT).sort((a,b)=>b.n-a.n);
  if(!types.length){box.innerHTML='<span class="mini">'+res.length+' concepts matched but none carried a recognized semantic type. Pick a type below.</span>';return;}
  const rows=types.map(t=>`<div class="styrow ${t.tui===AXB.tui?'acc':''}"><span class="stytree">${esc(t.tree)}</span> ${esc(t.name)} <span class="mut">&times;${t.n}</span>`+
    `<button class="ok mini" onclick="axbSet('${t.tui}')">${t.tui===AXB.tui?'✓ axis type':'use as axis type'}</button>`+
    `<button class="mini" onclick="stnToggle(this,'${t.tui}')">tree</button>`+
    `<div class="mini">e.g. ${esc(t.ex.join(', '))}</div></div>`).join('');
  box.innerHTML=`<div class="mini" style="margin-bottom:5px">${types.length} semantic type${types.length===1?'':'s'} across ${res.length} matching concepts — click one to set the axis type:</div><div class="stylist">${rows}</div>`;}
function axbRenderSel(){const box=$('#axsel');if(!box)return;const t=(SEMTYPES||[]).find(x=>x.tui===AXB.tui);
  if(!t){box.innerHTML=`<div style="display:flex;align-items:center;gap:7px">${IC.warn}<span style="color:var(--warn);font-weight:500">Axis type not set</span></div>`+
    `<div class="mini" style="margin-top:5px">Run the query or browse the types to choose one — value searches are unconstrained until then.</div>`;return;}
  const sub=(SEMTYPES||[]).filter(x=>stnUnder(x.tree,t.tree));
  box.innerHTML=`<span class="tnm">${esc(t.name)}</span> <span class="chip tui">${esc(t.tree)}</span>`+
    `<div class="mini" style="margin-top:4px">value searches constrained to <b>${sub.length}</b> semantic type${sub.length===1?'':'s'} (the axis subtree)</div>`+
    (t.definition?`<div class="def show" style="margin-top:7px">${esc(t.definition)}</div>`:'')+
    `<div class="subtree" style="margin-top:8px">${stnPlaceHTML(t.tui)}</div>`;}
function axbPicker(){const box=$('#styresults');if(!box)return;const q=(($('#styq')||{}).value||'').toLowerCase();
  box.innerHTML=(SEMTYPES||[]).filter(t=>!q||(t.name+' '+t.tui+' '+t.tree).toLowerCase().includes(q)).slice(0,80).map(t=>
    `<div class="styrow ${t.tui===AXB.tui?'acc':''}"><span class="stytree">${esc(t.tree)}</span> ${esc(t.name)}`+
    `<button class="ok mini" onclick="axbSet('${t.tui}')">${t.tui===AXB.tui?'✓ chosen':'choose'}</button>`+
    `<button class="mini" onclick="stnToggle(this,'${t.tui}')">tree</button>`+
    (t.definition?`<div class="def show">${esc(t.definition)}</div>`:'')+`</div>`).join('');}
function axbSet(tui){AXB.tui=tui;axbRenderSel();axbPicker();}
// tree-number topology: levels below a letter root have no dot (A -> A1 -> A1.1)
function stnUnder(tree,p){return !!tree&&(tree===p||(tree.startsWith(p)&&(p.length===1||tree[p.length]==='.')));}
function stnParents(tree){const ps=[];if(!tree)return ps;const segs=tree.split('.');
  if(segs[0].length>1)ps.push(segs[0][0]);
  for(let i=1;i<segs.length;i++)ps.push(segs.slice(0,i).join('.'));return ps;}
function stnParentOf(tree){const ps=stnParents(tree);return ps.length?ps[ps.length-1]:null;}
function stnPlaceHTML(tui,noclick){const t=(SEMTYPES||[]).find(x=>x.tui===tui);if(!t)return '<i>type not found</i>';
  const nm=n=>noclick?esc(n.name):`<a href="#" onclick="axbSet('${n.tui}');return false">${esc(n.name)}</a>`;
  const node=(n,inner)=>`<div class="stn-node${n.tui===tui?' hl':''}"><span class="stn-tree">${esc(n.tree)}</span> `+
    `${nm(n)}`+
    (inner?`<div class="stn-kids">${inner}</div>`:'')+`</div>`;
  const kidsOf=n=>(SEMTYPES||[]).filter(x=>stnParentOf(x.tree)===n.tree)
                                .sort((a,b)=>a.tree<b.tree?-1:1);
  const sub=n=>node(n,kidsOf(n).map(sub).join(''));
  const chain=stnParents(t.tree).map(pt=>(SEMTYPES||[]).find(x=>x.tree===pt)).filter(Boolean);
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
  AXB.prefs=($('#axprefs')||{}).value??AXB.prefs;
  const body={dimension:AXB.dimension,semantic_type:AXB.tui||'',query:AXB.query,note:AXB.note,
    preferred_sabs:AXB.prefs||''};
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
    `<span class="chip st-${esc(e.status)}">${esc(e.status)}</span>`+(e.curated?' <span class="badge">curated</span>':'')+needChips(e)+
    `<span class="spacer"></span><span id="msg"></span>${nextBtn(e.key)}<button data-write onclick="rebuild('${jsq(e.dimension)}')" title="Re-queries UMLS for this dimension's values only">Rebuild this dimension</button>`,
    e.dim_sty_tui?`axis semantic type: <b>${esc(e.dim_sty_name||e.dim_sty_tui)}</b> <span class="mono" style="font-size:11px">${esc(e.dim_sty_tree||'')}</span> — value search is constrained to its subtree unless widened below`
      :`the ${esc(e.dimension)} axis is untyped — value search runs unconstrained`);
  const slot=e.cui?` <span class="sabslot" data-cui="${esc(e.cui)}" data-root="${esc(e.root_source||'')}" data-prefs="${esc((e.sab_prefs||[]).join(','))}">`+
      (e.root_source?`<span class="sab">${esc(e.root_source)}</span>`:'')+`</span>`:'';
  const pend=e.decision==='accept'&&(e.status!=='mapped'||e.decision_cui!==e.cui);
  const cur=pend?`<span class="now">accepted &rarr; <b id="decname"><span class="cui">${esc(e.decision_cui)}</span></b>`+
      ` <span class="chip">${esc(e.relation||'exact')}</span> <span class="mini">— Rebuild folds it into the crosswalk</span></span>`
    :e.status==='mapped'?`<span class="now">mapped &rarr; <b>${esc(e.matched_name)}</b> <span class="cui">${esc(e.cui)}</span>${slot}`+
      (e.curated?` <span class="badge">${e.fetched?'curated · fetched':'curated'}</span>`
        :e.decision==='accept'?' <span class="badge">confirmed</span>':' <span class="mini">(auto)</span>')+`</span>`:
    e.status==='unmapped'?`<span class="now">unmapped${e.curated?' <span class="badge">curator</span>':''}</span>`:
    `<span class="now">review</span>`;
  const filt=e.dim_sty_tui?`<span class="chip" style="cursor:pointer" onclick="showAxisTree()" `+
      `title="click to see this type's place in the Semantic Network (ancestors, siblings, descendants)">`+
      `Semantic type: <b>&nbsp;${esc(e.dim_sty_name||e.dim_sty_tui)}</b>&nbsp;· <span class="mono">${esc(e.dim_sty_tree||e.dim_sty_tui)}</span>&nbsp;+ subtree ▾</span>`
    :`<span class="chip warnc">${IC.warn} axis untyped — search unconstrained</span>`;
  const relSel=RELATIONS.map(r=>`<option value="${r}"${(e.decision==='accept'?e.relation||'exact':'exact')===r?' selected':''}>${r}</option>`).join('');
  // a considered verdict without its argument (server code no-rationale)
  const norat=(e.needs||[]).includes('no-rationale')?`<div class="notice">${IC.warn}<span>${esc(needLabel('no-rationale').desc)} — open <b>“No faithful concept”</b> to add one</span></div>`:'';
  $('#content').innerHTML=`
   <div class="card"><h3>GEM meaning</h3><div style="font-size:13.5px">${esc(e.meaning)||'<span class="mini">(no gloss)</span>'}</div>
     <div class="mini" style="margin-top:4px">query used: <b>${esc(e.query)}</b></div></div>
   <div class="card"><h3>Decision</h3>${cur}${e.error?` <span style="color:var(--danger)">${esc(e.error)}</span>`:''}
     ${e.relation?` <span class="chip" title="how the recorded decision relates the concept to the GEM token">relation: <b>${esc(e.relation)}</b></span>`:''}
     ${norat}
     <div class="curbar">
       ${e.status==='mapped'&&e.cui&&!e.decision?`<button class="ok" data-write onclick="decide('accept','${jsq(e.cui)}',{relation:(($('#arel')||{}).value||'exact')})" title="record the harness mapping as your accepted decision (with the 'accept as' relation)">Confirm mapping ✓</button>`:''}
       <span class="mini" title="how an accepted concept relates to the GEM token — sent with the next accept">accept as</span>
       <select id="arel" class="mini" title="how the accepted concept relates to the GEM token">${relSel}</select>
       <button class="warn" data-write id="btn-unmapped">No faithful concept</button>
       <button data-write onclick="decide('clear')">Clear decision</button>
       ${e.note?`<span class="mini">note: ${esc(e.note)}</span>`:''}
     </div>
     <textarea id="note" placeholder="optional note / rationale">${esc(e.note||'')}</textarea>
     ${rationaleHTML(e)}
   </div>
   <div class="card"><h3>Query candidates · ${e.candidates.length}</h3>${e.candidates.map(c=>candHTML(c,null,'query')).join('')||'<span class="mini">none returned by the harness query</span>'}</div>
   <div class="card"><h3>Search the Metathesaurus <span style="margin-left:6px">${filt}</span>`+
     `<span class="hint">preferred: ${(e.sab_prefs||[]).length?esc(e.sab_prefs.join(' › ')):'none — set in ⚙ Settings'} · search: ${esc(STATE.search_backend||'UTS')}${umlsOff()?' — <a href="#" onclick="showKeyDialog();return false">connect UMLS</a>':(STATE.search_backend||'UTS')==='UTS'?' (local index not active — see ⚙)':''}</span></h3>
     <div class="searchbar"><input id="sq" placeholder="concept term…" value="${esc(e.token?String(e.token).replace(/_/g,' ').toLowerCase():e.query)}">
       <select id="sscope" title="widen the search beyond the axis subtree"${e.dim_sty_tui?'':' disabled'}>
         <option value="axis"${e.dim_sty_tui?'':' disabled'}>within axis subtree</option>
         <option value="all"${e.dim_sty_tui?'':' selected'}>all semantic types</option></select>
       <select id="smatch" title="how the term is matched">
         <option value="words">match: words</option><option value="exact">match: exact</option>
         <option value="normalizedWords">match: normalized</option><option value="partial">match: partial (any word)</option></select>
       <select id="ssab"><option value="">all sources</option><option>MSH</option><option>NCI</option><option>SNOMEDCT_US</option><option>GO</option><option>HPO</option></select>
       <button class="primary" onclick="runSearch()">Search</button>
       ${e.dim_sty_filter?`<button class="mini" onclick="browseAxis()" title="list every concept of the axis subtree (local index); the search box narrows the list as you type">browse axis</button>`:''}
       <button class="mini" onclick="expandTerms()" title="ontology-aware expansion: each query word is replaced by its is_a children/parents (organism → animal, …) and the variants are re-searched">expand terms</button></div>
     <div id="sresults"></div></div>`;
  $('#sq').addEventListener('keydown',ev=>{if(ev.key==='Enter')runSearch();});
  $('#btn-unmapped').addEventListener('click',openUnmapped);
  wireNext(e.key);
  // changing "accept as" on an existing acceptance re-records it live
  const ar=$('#arel');
  if(ar)ar.addEventListener('change',()=>{
    if(SEL&&SEL.decision==='accept'&&SEL.decision_cui){
      decide('accept',SEL.decision_cui,{relation:ar.value});
      msg('relation → '+ar.value);}
    else if(SEL&&SEL.status==='mapped'&&SEL.cui&&!SEL.decision){
      // no decision yet: changing "accept as" on a harness mapping accepts it at that relation
      decide('accept',SEL.cui,{relation:ar.value});
      msg('accepted '+SEL.cui+' as '+ar.value);}});
  enrichSabs($('#content'));enrichSlots($('#content'));
  // resolve the accepted CUI's name for the pending-decision line
  if(pend&&e.decision_cui){(async()=>{try{
    const j=await (await fetch('/api/concept?cui='+encodeURIComponent(e.decision_cui))).json();
    const el=$('#decname');
    if(el&&j&&j.evidence&&j.evidence.name)el.innerHTML=esc(j.evidence.name)+' <span class="cui">'+esc(e.decision_cui)+'</span>';
  }catch(err){}})();}
  // the candidates' STN links need the Semantic Network; if it arrived after
  // this render, paint once more (guarded to the same route)
  if(!SEMTYPES)loadSemTypes().then(()=>{if(ROUTE.view==='value'&&ROUTE.key===e.key)renderValue();});}
// The recorded argument for a decision: relation chip (above), the rejected
// candidates with their failing criterion, and the protocol actually followed.
function rationaleHTML(e){const rej=e.rejected||[],p=e.protocol||{};
  if(!rej.length&&!Object.keys(p).length)return '';
  const rows=rej.map(r=>`<tr><td>${esc(r.name||'')}</td><td class="cui">${esc(r.cui)}</td><td>${esc(r.sab||'')}</td>`+
    `<td><b title="${esc(CRITERIA[r.fails]||'')}">${esc(r.fails)}</b></td><td>${esc(r.why||'')}</td></tr>`).join('');
  const tbl=rej.length?`<table class="et" style="margin-top:6px"><tr><th>rejected candidate</th><th>CUI</th><th>SAB</th><th title="criterion: A denotation · B granularity · C set membership · D domain sense">fails</th><th>why</th></tr>${rows}</table>`:'';
  return `<div class="evsec"><div class="evh">Recorded rationale</div>${tbl}${protocolLine(p)}</div>`;}
function protocolLine(p){if(!p||!Object.keys(p).length)return '';
  const part=[];
  if((p.queries||[]).length)part.push('queries '+p.queries.map(q=>'“'+esc(q)+'”').join(', '));
  if((p.scopes||[]).length)part.push('scope '+esc(p.scopes.join(', ')));
  if((p.match||[]).length)part.push('match '+esc(p.match.join(', ')));
  if((p.sabs||[]).length)part.push('sabs '+esc(p.sabs.join(', ')));
  if(p.umls)part.push(esc(p.umls));
  return `<div class="mini mono" style="margin-top:5px">protocol: ${part.join(' · ')}</div>`;}
// remember every candidate card rendered for the selected value (query
// candidates and search hits alike) so the unmapped argument can list them
function noteSeen(c,origin){if(!SEL||!c||!c.cui)return;
  const m=SEEN[SEL.key]||(SEEN[SEL.key]={});
  if(!m[c.cui])m[c.cui]={cui:c.cui,name:c.name||'',root_source:c.src||c.root_source||'',
    semantic_types:(c.sty||c.semantic_types||[]).slice(),origin:origin||'search'};
  else if(c.name&&!m[c.cui].name)m[c.cui].name=c.name;}
// auto-filled protocol for the selected value: the harness query (its scope
// is the axis when the dimension is typed) plus every search run in-session
function buildProtocol(){const log=SEARCHLOG[SEL.key]||[];
  const uniq=a=>[...new Set(a.filter(Boolean))];
  const hq=SEL.query?[SEL.query]:[],hs=SEL.query?[SEL.dim_sty_tui?'axis':'all']:[];
  const hm=['words','exact','normalizedWords','normalizedString','partial'].includes(SEL.search_type)?[SEL.search_type]:[];
  return {queries:uniq(hq.concat(log.map(l=>l.q))),scopes:uniq(hs.concat(log.map(l=>l.scope))),
    match:uniq(hm.concat(log.map(l=>l.match))),sabs:uniq((SEL.sab_pref?[SEL.sab_pref]:[]).concat(log.map(l=>l.sab))),
    umls:'UTS current, queried '+new Date().toISOString().slice(0,10)};}
// "No faithful concept": argue it. Every candidate seen for this value gets a
// failing criterion (A-D) and a one-line why; the protocol is auto-filled.
function openUnmapped(){if(!SEL)return;const e=SEL;
  const seen=Object.values(SEEN[e.key]||{});
  const prev={};(e.rejected||[]).forEach(r=>{prev[r.cui]=r;
    if(!seen.some(s=>s.cui===r.cui))seen.push({cui:r.cui,name:r.name||'',root_source:r.sab||'',semantic_types:[],origin:'recorded'});});
  const rank={query:0,search:1,recorded:2};
  seen.sort((a,b)=>(rank[a.origin]??9)-(rank[b.origin]??9));
  const list=seen.slice(0,50),more=seen.length-list.length;   // server cap: RATIONALE_MAXITEMS
  const opts=k=>`<option value="">—</option>`+Object.keys(CRITERIA).map(c=>`<option value="${c}" title="${esc(CRITERIA[c])}"${k===c?' selected':''}>${c}</option>`).join('');
  const rows=list.map(c=>{const pr=prev[c.cui]||{};
    return `<tr data-cui="${esc(c.cui)}" data-name="${esc(c.name)}" data-sab="${esc(c.root_source||'')}">`+
      `<td>${esc(c.name)}<div class="mini">${esc((c.semantic_types||[]).join(', '))}${c.origin==='query'?' · harness query':c.origin==='recorded'?' · recorded earlier':''}</div></td>`+
      `<td class="cui">${esc(c.cui)}</td><td>${esc(c.root_source||'')}</td>`+
      `<td><select class="rj-fails" title="A · ${esc(CRITERIA.A)}&#10;B · ${esc(CRITERIA.B)}&#10;C · ${esc(CRITERIA.C)}&#10;D · ${esc(CRITERIA.D)}">${opts(pr.fails)}</select></td>`+
      `<td><input class="rj-why" maxlength="300" placeholder="one line" value="${esc(pr.why||'')}" style="width:100%"></td></tr>`;}).join('');
  const legend=Object.keys(CRITERIA).map(k=>`<div><b>${k}</b> ${esc(CRITERIA[k])}</div>`).join('');
  const body=`<div class="mini" style="margin-bottom:8px">Record <b>${esc(String(e.token))}</b> as having no faithful UMLS concept. `+
    `Say why each candidate you saw fails — the criterion it fails and one line of why.</div>`+
    (list.length?`<div style="max-height:46vh;overflow:auto"><table class="et"><tr><th>candidate</th><th>CUI</th><th>SAB</th><th>fails</th><th>why</th></tr>${rows}</table></div>`+
      (more>0?`<div class="mini">+${more} more candidates seen, not listed</div>`:'')
     :`<div class="mini" style="font-style:italic">No candidates were seen for this value — the harness query returned none and no search has been run here. The finding is recorded with an empty rejected list.</div>`)+
    `<details style="margin-top:6px"><summary class="mini" style="cursor:pointer">criteria</summary><div class="mini" style="margin:4px 0 0 8px">${legend}</div></details>`+
    `<div class="evsec"><div class="evh">Protocol (auto-filled)</div>${protocolLine(buildProtocol())||'<span class="mini">nothing searched yet</span>'}</div>`+
    `<div class="evsec"><div class="evh">Note</div><textarea id="unote" placeholder="optional note / rationale">${esc(($('#note')||{}).value||e.note||'')}</textarea></div>`+
    `<div style="display:flex;align-items:center;gap:10px;margin-top:10px"><button class="warn" data-write id="urec">Record: no faithful concept</button><span id="umsg" class="mini" style="color:var(--danger)"></span></div>`;
  showModal('No faithful concept — '+esc(String(e.token)),body);
  $('#urec').addEventListener('click',recordUnmapped);}
async function recordUnmapped(){const rows=[...document.querySelectorAll('#modal tr[data-cui]')];
  const rejected=[];
  rows.forEach(tr=>{const f=tr.querySelector('.rj-fails').value;if(!f)return;
    rejected.push({cui:tr.dataset.cui,name:tr.dataset.name,sab:tr.dataset.sab,fails:f,why:tr.querySelector('.rj-why').value.trim()});});
  if(rows.length&&!rejected.length){$('#umsg').textContent='give at least one candidate a failing criterion (A–D) — or clear the list by accepting one';return;}
  const note=($('#unote')||{}).value||'';
  const ok=await decide('unmapped',null,{relation:'none',rejected,protocol:buildProtocol(),note});
  if(ok)closeModal();else $('#umsg').textContent=($('#msg')||{}).textContent||'not saved';}
function candHTML(c,mark,origin){const acc=SEL&&SEL.decision_cui===c.cui;noteSeen(c,origin);
  const badge=mark==='in'?' <span class="badge">in axis branch</span>'
    :mark==='out'?' <span class="badge bad">outside axis</span>':'';
  const st=mostSpecificTui(c.sty||c.semantic_types);
  const stn=st?` · <a href="#" class="stnlink" onclick="showCompare('${st.tui}');return false" `+
    `title="${esc(st.name)} — click to see its place relative to the axis type">${esc(st.tree)}</a>`:'';
  return `<div class="cand ${acc?'acc':''}" data-cui="${esc(c.cui)}"><div class="row"><span class="n">${esc(c.name)} <span class="cui">${esc(c.cui)}</span></span>`+
    `<button class="mini" onclick="loadDef('${c.cui}',this)">evidence</button>`+
    `<button class="mini" onclick="descendFrom(this,'${c.cui}')" title="walk this concept's is_a descendants across its vocabularies, ranked against the search text — for when the direct search misses a more specific match">↓ desc</button>`+
    `<button class="ok" data-write onclick="decide('accept','${c.cui}',{relation:(($('#arel')||{}).value||'exact')})">${acc?'✓ accepted':'accept'}</button></div>`+
    `<div class="sty">${esc((c.sty||c.semantic_types||[]).join(', '))}${c.src||c.root_source?` · <span title="root source of the concept's preferred name (MTH = the Metathesaurus itself) — full vocabulary membership follows">${esc(c.src||c.root_source)}</span>`:''}${stn}${badge}</div>`+
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
  const pathRows=(e.sty_path||[]).map((p,i)=>`<tr><td>${i?'<span class="mut">&uarr;</span>':'<b>STY</b>'}</td><td>${esc(p.name)}</td><td class="stn">${esc(p.tree)}</td></tr>`).join('');
  const axbadge=axis?(e.under_axis?' <span class="badge">in axis branch</span>':' <span class="badge bad">outside axis branch</span>'):'';
  const styBlock=`<div class="evsec"><div class="evh">Semantic type${axbadge}<button class="mini" onclick="toggleSubtree(this,'${esc(spec.tui||'')}','${axis?esc(axis.tui):''}')">subtree</button></div>`+
    `<table class="et"><tr><th></th><th>STY</th><th>STN</th></tr>${pathRows}`+
    (axis?`<tr class="axisrow"><td><b>axis</b></td><td>${esc(axis.name)}</td><td class="stn">${esc(axis.stn)}</td></tr>`:'')+
    `</table><div class="subtree" style="display:none"></div></div>`;
  const vrows=(e.atom_rows||[]).map(a=>`<tr class="${a.obsolete?'obs':''}"><td>${esc(a.sab)}</td><td>${esc(a.str)}</td><td style="white-space:nowrap">${ttyHTML(a.tty)}</td><td class="cui">${esc(a.code)}</td></tr>`).join('');
  const vocBlock=`<div class="evsec"><div class="evh">Vocabularies (${(e.sabs||[]).length} sources, English)</div><table class="et"><tr><th>SAB</th><th>STR</th><th>TTY</th><th>Code</th></tr>${vrows||'<tr><td colspan=4><i>none</i></td></tr>'}</table></div>`;
  const rid=r=>esc(r.cui||r.code||'');
  const act=r=>r.cui?`<button class="mini" onclick="openConcept('${r.cui}','${jsq(r.name)}')" title="pull this concept into the search results to inspect or accept it">open</button>`
    :`<button class="mini" onclick="findByName('${jsq(r.name)}')" title="source-asserted (no CUI here) — search it by name">find</button>`;
  const rrows=(e.relations||[]).map(r=>`<tr><td class="dir ${r.dir}">${r.dir==='up'?'&uarr; is_a':'&darr; is_a'}</td><td>${esc(r.name)}</td><td class="cui">${rid(r)}</td><td>${esc((r.sabs||[]).join(', '))}</td><td>${act(r)}</td></tr>`).join('');
  const relBlock=`<div class="evsec"><div class="evh">Hierarchy (is_a)</div><table class="et"><tr><th>dir</th><th>concept</th><th>id</th><th>sources</th><th></th></tr>${rrows||'<tr><td colspan=5><i>no concept-level is_a edges — hierarchies here are usually source-asserted: use the ↓ desc button for children, Rollup for ancestors</i></td></tr>'}</table></div>`;
  const org=(e.other_relations||[]);
  const orInner=org.map(g=>{
    const items=g.items.map(it=>`<tr><td>${esc(it.name)}</td><td class="cui">${rid(it)}</td><td>${esc((it.sabs||[]).join(', '))}</td><td>${act(it)}</td></tr>`).join('');
    const more=g.n>g.items.length?`<tr><td colspan=4 class="mut">+${g.n-g.items.length} more</td></tr>`:'';
    return `<tr class="orh"><td colspan=4>${esc(g.rela)} <span class="mut">(${g.n})</span></td></tr>${items}${more}`;}).join('');
  const otherBlock=org.length?`<div class="evsec"><div class="evh">Other relations<button class="mini" data-k="${org.length}" onclick="toggleOther(this)">show ${org.length} kinds</button></div><div class="otherbox" style="display:none"><table class="et"><tr><th>concept</th><th>id</th><th>sources</th><th></th></tr>${orInner}</table></div></div>`:'';
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
  const inSub=(SEMTYPES||[]).filter(t=>stnUnder(t.tree,rt.tree));
  const render2=n=>{const kids=inSub.filter(t=>stnParentOf(t.tree)===n.tree);
    const hl=n.tui===specTui?' hl':(n.tui===axisTui?' ax':'');
    return `<div class="stn-node${hl}"><span class="stn-tree">${esc(n.tree)}</span> ${esc(n.name)}`+
      (kids.length?`<div class="stn-kids">${kids.map(render2).join('')}</div>`:'')+`</div>`;};
  box.innerHTML=render2(rt);}
async function loadRollup(box,cui,sab){box.innerHTML='rolling up is_a ancestors…';
  const j=await (await fetch('/api/rollup?cui='+cui+(sab?'&use_sab='+encodeURIComponent(sab):''))).json();
  const rows=(j.rollup||[]).map(a=>`<tr><td>${esc(a.name)}</td><td class="cui">${esc(a.code)}</td><td>${esc(a.sab)}</td>`+
    `<td><button class="mini" onclick="findByName('${jsq(a.name)}')" title="search this ancestor by name to get its concept">find</button></td></tr>`).join('');
  const opts=j.sabs||[];
  const nav=opts.length?`<div class="mini2">vocabulary: <a href="#" data-cui="${cui}" onclick="rollNav(this,'');return false">auto</a>${opts.map(s=>` &middot; <a href="#" data-cui="${cui}" onclick="rollNav(this,'${esc(s)}');return false">${esc(s)}</a>`).join('')}${sab?' &mdash; <b>'+esc(sab)+'</b>':''}</div>`:'';
  box.innerHTML=nav+`<table class="et"><tr><th>is_a ancestor</th><th>code</th><th>vocab</th><th></th></tr>${rows||'<tr><td colspan=4><i>no is_a ancestors in English vocabularies</i></td></tr>'}</table>`;}
function rollNav(a,sab){loadRollup(a.closest('.rollbox'),a.dataset.cui,sab||null);}
async function runSearch(){const q=$('#sq').value,sab=$('#ssab').value;
  // direct CUI lookup: paste a CUI to pull that exact concept as a candidate
  // card (then evidence / ↓ desc / relations work from it)
  const cuiM=(q||'').trim().match(/^C\d{7}$/i);
  if(cuiM){const box=$('#sresults');box.dataset.mode='search';
    box.innerHTML='<span class="mini">fetching '+esc(cuiM[0].toUpperCase())+'…</span>';
    const j=await (await fetch('/api/concept?cui='+cuiM[0].toUpperCase()+(SEL&&SEL.dim_sty_tui?'&axis='+SEL.dim_sty_tui:''))).json();
    const ev=(j||{}).evidence||{};
    if(ev.error||!ev.name){box.innerHTML='<span class="mini">'+esc(ev.error||'concept not found')+'</span>';return;}
    box.innerHTML='<div class="mini" style="margin-bottom:5px">1 concept by CUI · '+esc(STATE.search_backend||'UTS')+'</div>'
      +candHTML({cui:cuiM[0].toUpperCase(),name:ev.name,root_source:'',semantic_types:(ev.semantic_types||[]).map(x=>x.name||x)});
    enrichSabs(box);return;}
  const scope=($('#sscope')||{}).value||'axis',stype=($('#smatch')||{}).value||'words';
  if(SEL){const log=SEARCHLOG[SEL.key]||(SEARCHLOG[SEL.key]=[]);
    if(!log.some(l=>l.q===q&&l.scope===scope&&l.match===stype&&l.sab===sab))log.push({q,scope,match:stype,sab});}
  const box=$('#sresults');box.dataset.mode='search';box.innerHTML='<span class="mini">searching…</span>';
  const stys=scope==='axis'?(SEL.dim_sty_filter||''):'';
  const url='/api/search?string='+encodeURIComponent(q)+(sab?'&sabs='+sab:'')+
    (stys?'&stys='+encodeURIComponent(stys):'')+(stype!=='words'?'&stype='+encodeURIComponent(stype):'');
  const r=await fetch(url);const j=await r.json();
  if(j.error){box.innerHTML='<span style="color:var(--danger)">'+esc(j.error)+'</span>';return;}
  await loadSemTypes();
  // when searching beyond the axis, mark each hit as inside/outside the axis branch
  const axSet=new Set((SEL.dim_sty_filter||'').split(',').filter(Boolean));
  const norm=s=>(s||'').toLowerCase();
  const tuiOf=nm=>{const t=(SEMTYPES||[]).find(x=>norm(x.name)===norm(nm));return t?t.tui:null;};
  const res=(j.results||[]).slice(0,20);
  const rows=res.map(c=>{let mark=null;
    if(axSet.size&&scope!=='axis'){const tus=(c.semantic_types||c.sty||[]).map(tuiOf).filter(Boolean);
      mark=tus.some(t=>axSet.has(t))?'in':'out';}
    return candHTML(c,mark);}).join('');
  const count=`<div class="mini" style="margin-bottom:5px">${res.length} result${res.length===1?'':'s'} · ${esc(STATE.search_backend||'UTS')}${res.length>=20?' (top 20 shown)':''}</div>`;
  box.innerHTML=rows?count+rows:( j.note?'<span class="mini" style="color:var(--warn)">'+esc(j.note)+'</span>'
    :scope==='axis'
    ?'<span class="mini">no results within the axis subtree.</span> <button class="mini" onclick="widen()">widen: search all semantic types</button>'
    :'<span class="mini">no results — try match: partial (any word), or a different term</span>');
  if(rows)enrichSabs(box);}
function widen(){const s=$('#sscope');if(s)s.value='all';runSearch();}
async function expandTerms(){if(!SEL)return;const box=$('#sresults');if(!box)return;
  const q=(($('#sq')||{}).value||'').trim();if(!q){box.innerHTML='<span class="mini">enter a query first</span>';return;}
  const scope=($('#sscope')||{}).value||'axis';
  const stys=scope==='axis'?(SEL.dim_sty_filter||''):'';
  box.dataset.mode='search';box.innerHTML='<span class="mini">expanding query terms through the hierarchy…</span>';
  const j=await (await fetch('/api/expand?q='+encodeURIComponent(q)+(stys?'&stys='+encodeURIComponent(stys):''))).json();
  if(j.error){box.innerHTML='<span style="color:var(--danger)">'+esc(j.error)+'</span>';return;}
  await loadSemTypes();
  const res=j.results||[];
  box.innerHTML=`<div class="mini" style="margin-bottom:5px">${res.length} concept${res.length===1?'':'s'} via ${j.n_variants} expanded variants of “${esc(q)}”${scope==='axis'&&stys?' (axis subtree — widen scope for more)':''}</div>`+
    res.map(r=>`<div class="mini" style="margin:6px 0 2px;color:var(--accent)">via ${esc(r.via)} — “${esc(r.variant)}”</div>`+candHTML(r)).join('')
    ||'<span class="mini">no variants matched — the query words may have no exactly-named concepts to pivot on</span>';
  if(res.length)enrichSabs(box);}
let AXBROWSE={};
async function browseAxis(){if(!SEL||!SEL.dim_sty_filter)return;const box=$('#sresults');if(!box)return;
  box.innerHTML='<span class="mini">loading the axis subtree…</span>';
  const dim=SEL.dimension;
  if(!AXBROWSE[dim]){
    const j=await (await fetch('/api/axisbrowse?stys='+encodeURIComponent(SEL.dim_sty_filter))).json();
    if(j.error){box.innerHTML='<span class="mini">'+esc(j.error)+'</span>';return;}
    AXBROWSE[dim]=(j.concepts||[]);}
  box.dataset.mode='browse';renderAxisBrowse();
  const sq=$('#sq');
  if(sq&&!sq.dataset.axb){sq.dataset.axb='1';
    sq.addEventListener('input',()=>{const b=$('#sresults');
      if(b&&b.dataset.mode==='browse'&&AXBROWSE[SEL&&SEL.dimension])renderAxisBrowse();});}}
function renderAxisBrowse(){const box=$('#sresults');if(!box)return;
  const all=AXBROWSE[SEL.dimension]||[];
  const q=(($('#sq')||{}).value||'').toLowerCase().trim();
  const hits=all.filter(c=>!q||(c.name||'').toLowerCase().includes(q));
  const shown=hits.slice(0,40);
  box.innerHTML=`<div class="mini" style="margin-bottom:6px">axis subtree: ${all.length} concepts · ${hits.length} match${q?' the filter':''} · showing ${shown.length} — type in the search box to narrow; Search returns to normal results</div>`+
    shown.map(c=>candHTML(c)).join('');
  enrichSabs(box);}
function findByName(name){const q=$('#sq');if(!q)return;q.value=name;
  const s=$('#sscope');if(s)s.value='all';runSearch();
  msg('searching for “'+name+'” across all semantic types');}
async function descendFrom(btn,cui){const box=btn.closest('.cand').querySelector('.def');
  const q=(($('#sq')||{}).value||'').trim();
  box.classList.add('show');box.innerHTML='<span class="mini">walking is_a descendants across vocabularies…</span>';
  const j=await (await fetch('/api/descend?cui='+encodeURIComponent(cui)+'&q='+encodeURIComponent(q))).json();
  if(j.error){box.innerHTML='<span class="mini">'+esc(j.error)+'</span>';return;}
  const rows=(j.matches||[]).map(m=>`<tr><td>${esc(m.name)}${m.parent?`<div class="mini">under ${esc(m.parent)}</div>`:''}</td>`+
    `<td class="cui">${esc(m.code)}</td><td>${esc(m.sab)}</td><td>${m.depth}</td><td>${m.score.toFixed(2)}</td>`+
    `<td><button class="mini" onclick="findByName('${jsq(m.name)}')" title="search this name to get its concept">find</button></td></tr>`).join('');
  const via=(j.anchors||[]).map(a=>a.sab).join(', ');
  box.innerHTML=`<div class="evh">is_a descendants${via?` via ${esc(via)}`:''}${q?` ranked vs “${esc(q)}”`:''} (depth ≤2)</div>`+
    (rows?`<table class="et"><tr><th>descendant</th><th>code</th><th>vocab</th><th>d</th><th>score</th><th></th></tr>${rows}</table>`
      :'<span class="mini">no is_a descendants in any of this concept’s vocabularies</span>');}
function openConcept(cui,name){const box=$('#sresults');if(!box)return;
  if(box.querySelector('[data-cui="'+cui+'"]')){msg(cui+' already in results');return;}
  const t=document.createElement('template');
  t.innerHTML=candHTML({cui,name,sty:[],src:''}).trim();
  box.prepend(t.content.firstChild);enrichSabs(box);
  msg('pulled '+cui+' into search results — accept it or open its evidence');}
// extra: optional rationale keys (relation / rejected / protocol / note) that
// travel with the verdict; a note given here wins over the Decision textarea.
async function decide(verdict,cui,extra){extra=extra||{};
  const note=extra.note!==undefined?extra.note:(($('#note')||{}).value||'');
  const body={key:SEL.key,verdict};if(cui)body.cui=cui;if(note)body.note=note;
  ['relation','rejected','protocol'].forEach(k=>{if(extra[k]!==undefined)body[k]=extra[k];});
  msg('saving…');const r=await fetch('/api/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json();if(j.error){msg('error: '+j.error);return false;}
  await loadState();msg('saved '+SEL.key+' ('+verdict+') — Rebuild to refresh status');return true;}
function openSettings(){const wp=((STATE&&STATE.prefs||{}).workspace||[]).join(', ');
  showModal('Settings',
    `<div style="font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--faint)">PREFERRED VOCABULARIES</div>`+
    `<div class="mini" style="margin:4px 0 8px">Ordered list. Decides which source is shown and ticked for every mapped concept and candidate, everywhere in the app.</div>`+
    `<div style="display:flex;gap:8px"><input id="prefsabs" value="${esc(wp)}" placeholder="e.g. SNOMEDCT_US, MSH, NCI, HPO" style="flex:1;font-family:var(--mono);font-size:12.5px">`+
    `<button class="primary" data-write onclick="savePrefs()">Save</button></div>`+
    `<div class="mini" style="margin-top:8px">Workspace default (inventory <span class="mono">meta.preferred_sabs</span>). A dimension can override it in its axis card; a value's own <span class="mono">sab:</span> hint in the inventory always comes first.</div>`+
    `<div style="margin-top:14px;font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--faint)">SERVER</div>`+
    `<div class="mini" style="margin-top:4px">started ${esc((STATE.server||{}).started||'?')} · running code saved ${esc((STATE.server||{}).code||'?')} — if the code date is older than your latest changes, restart the Studio (Ctrl-C, then <span class="mono">gem-umls-adjudicate</span>)</div>`+
    `<div style="margin-top:14px;font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--faint)">UMLS API KEY</div>`+
    (umlsOff()?`<div style="font-size:12.5px;margin-top:4px;color:var(--warn)">not connected — searches, evidence, and rebuilds are disabled</div><button class="primary" style="margin-top:6px" onclick="showKeyDialog()">Connect UMLS…</button>`
      :`<div style="font-size:12.5px;margin-top:4px">connected · key from ${esc((STATE.umls||{}).key_source||'?')}</div><button class="mini" style="margin-top:6px" onclick="showKeyDialog()">use a different key</button>`)+
    `<div style="margin-top:14px;font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--faint)">SEARCH BACKEND</div>`+
    `<div style="font-size:12.5px;margin-top:4px">${esc(STATE.search_backend||'UTS')}${(STATE.search_backend||'UTS')==='UTS'?' — the optional local index (faster search, typo-tolerant matching, axis browse) is not loaded':''}</div>`+
    (STATE.search_backend_note?`<div class="mini" style="margin-top:3px;color:var(--warn)">probe: ${esc(STATE.search_backend_note)}</div>`:'')+
    ((STATE.search_backend||'UTS')==='UTS'?`<div class="mini" style="margin-top:4px">To enable it: download a UMLS release with your license, create the database (<span class="mono">createdb umls; psql -d umls -c 'CREATE EXTENSION pg_trgm'</span>), load it (<span class="mono">gem-umls-load-local --rrf-dir ~/umls/2026AA/META --release 2026AA</span>) and restart the Studio. Full recipe: <span class="mono">data/umls/README.md</span>.</div>`:'')+
    `<div style="margin-top:14px;font-size:10.5px;font-weight:600;letter-spacing:.09em;color:var(--faint)">WORKSPACE</div>`+
    `<div class="mono" style="font-size:11.5px;word-break:break-all;margin-top:4px">${esc(STATE.workspace||'')}</div>`);
  const i=$('#prefsabs');if(i){attachSabTypeahead(i,savePrefs);i.focus();}}
async function savePrefs(){const v=($('#prefsabs')||{}).value||'';msg('saving preferences…');
  const j=await (await fetch('/api/prefs',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({preferred_sabs:v})})).json();
  if(j.error){msg('error: '+j.error);return;}
  for(const k in SABCACHE)delete SABCACHE[k];   // labels depend on prefs; recompute lazily
  closeModal();await loadState();msg('preferred vocabularies: '+((j.preferred_sabs||[]).join(' › ')||'none'));}
async function rebuild(dim){msg(dim?('rebuilding '+dim+' (querying UMLS)…'):'rebuilding ALL dimensions (querying UMLS)…');
  const r=await fetch('/api/rebuild',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(dim?{dim}:{})});
  const j=await r.json();
  if(j.error){msg('error: '+j.error);return;}
  await loadState();const c=STATE.counts||{};
  msg((dim?dim+' rebuilt':'all rebuilt')+' — '+(c.mapped||0)+' mapped · '+(c.review||0)+' review · '+(c.unmapped||0)+' unmapped of '+(c.total||0)+' values · '+(c.needs||0)+' need review');}
installKeyGuard();loadState();loadSemTypes();
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
    ap.add_argument("--search-backend", choices=["auto", "uts", "local"],
                    default="auto",
                    help="auto (default): use a local UMLS index when one is "
                         "loaded, else UTS — the released tool needs only a "
                         "UTS key; 'uts' never touches the local index; "
                         "'local' requires one and fails fast without it.")
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

    global SEARCH_BACKEND, UTS_ONLINE, KEY_SOURCE, LOCAL_INDEX
    key, KEY_SOURCE = find_api_key()
    if key:
        client = UTSClient(key, cache_dir=H.CACHE_DIR)
        UTS_ONLINE = True
        print(f"UMLS: key loaded from {KEY_SOURCE}.")
    else:
        # Axis construction needs only the Semantic Network (reference data), so
        # start without a key; every UMLS-backed request then answers with
        # needs_key and the browser opens the Connect UMLS walkthrough.
        print("WARNING: no UMLS API key found (checked $UMLS_API_KEY, "
              f"{H.BASE / '.envrc'}, {KEY_FILE}).\n"
              "  The workspace opens READ-ONLY: you can browse it, but adding "
              "or changing a dimension,\n"
              "  a value or a decision needs a key. The Studio will prompt for "
              "one.\n"
              f"  1. Create a free UTS account: {UTS_SIGNUP_URL}\n"
              "     (NLM approves the UMLS license request, usually within a "
              "few business days)\n"
              f"  2. Copy the API key from your UTS profile: {UTS_PROFILE_URL}\n"
              "  3. Paste it into the Studio's Connect UMLS dialog (it can be "
              "remembered on this machine),\n"
              "     or export UMLS_API_KEY=<key> and restart.")
        client = NullClient()
        SEARCH_BACKEND = "OFFLINE — no UMLS key"
        globals()["SEARCH_BACKEND_NOTE"] = ("no UMLS_API_KEY in the environment: "
            "use Connect UMLS in the Studio, or export UMLS_API_KEY (the repo "
            ".envrc exports it under direnv)")
    # The local PostgreSQL index is an OPTIONAL accelerator each user builds
    # from their own licensed UMLS copy (gem-umls-load-local; see
    # data/umls/README.md) -- it is never distributed with the tool. Released
    # behavior needs only a UTS key: --search-backend auto silently falls
    # back to UTS when no index is reachable; 'browse axis' then explains
    # what it needs instead of appearing broken.
    if args.search_backend != "uts":
        try:
            from forome.gem.umls.local_umls import PgUMLSClient
            _pg = PgUMLSClient(os.environ.get("GEM_UMLS_DSN") or None)
            _rel = _pg.release()
            if _rel:
                client = HybridClient(_pg, client)
                LOCAL_INDEX = True
                SEARCH_BACKEND = f"local {_rel.get('version')}"
                print(f"Search backend: local UMLS index {_rel.get('version')}; "
                      "concept details via UTS.")
            elif args.search_backend == "local":
                raise SystemExit("--search-backend local: no umls_release row -- "
                                 "load an index with gem-umls-load-local first.")
            else:
                globals()["SEARCH_BACKEND_NOTE"] = ("database reachable but no "
                                                   "umls_release row (index not loaded)")
        except SystemExit:
            raise
        except Exception as ex:  # noqa: BLE001 -- no driver / DB: UTS only
            if args.search_backend == "local":
                raise SystemExit(f"--search-backend local: {ex}")
            globals()["SEARCH_BACKEND_NOTE"] = (f"{type(ex).__name__}: {ex} "
                f"[python: {sys.executable}]")
            print(f"Local index not used ({SEARCH_BACKEND_NOTE}); search via UTS.")

    if not H.INVENTORY.is_file() and not CROSSWALK.is_file():
        print(f"Workspace {DATA_DIR} has no inventory or crosswalk yet -- "
              f"starting empty; use “New dimension” to define the first axis, "
              f"then “Add value” for its values.")

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
