#!/usr/bin/env python3
"""Render the UMLS + OMOP/CDM crosswalk as a LaTeX supplement section.

Reads the harness output (``data/umls/umls_crosswalk.yaml``), overlays the
curator's decisions (``data/umls/adjudications.yaml``: the typed *relation*
of every accepted concept and the structured rationale of every argued
gap) and the hand-authored OMOP examples (``data/umls/omop_cdm_examples.yaml``),
and writes a self-contained ``.tex`` section: an honest UMLS concept table
(grouped by dimension; mapped / review / unmapped status surfaced; one
relation column) plus an illustrative OMOP/CDM positioning table.

This produces its own supplement section (``paper/sections/s18_umls_crosswalk.tex``,
``\\input`` by ``supplement.tex``); it does not modify ``s15_crosswalk.tex``
(the SO/HPO/NCBITaxon/ECO/SEPIO/GA4GH-VA/FHIR crosswalk). The generated file
uses ``longtable`` and ``booktabs``.

Usage:
    gem-umls-render                       # regenerate the supplement section
    gem-umls-render --crosswalk data/umls/umls_crosswalk.demo.yaml \\
        --out data/umls/s18_umls_crosswalk.preview.tex
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from forome.gem.umls import build_umls_crosswalk as H
from forome.gem.umls._paths import DATA_DIR, PAPER_SECTIONS

DEFAULT_CROSSWALK = DATA_DIR / "umls_crosswalk.yaml"
DEFAULT_OMOP = DATA_DIR / "omop_cdm_examples.yaml"
DEFAULT_OUT = PAPER_SECTIONS / "s18_umls_crosswalk.tex"

_TEX = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def tex(s) -> str:
    if s is None:
        return ""
    return "".join(_TEX.get(c, c) for c in str(s))


def _adj_key(e: dict) -> str:
    return H._adj_key(e["dimension"], None if e.get("kind") == "axis" else e.get("token"))


def _argued(a: dict) -> bool:
    """An unmapped verdict counts as *argued* when it carries a rationale:
    rejected near-misses and/or the search protocol that failed."""
    return bool(a.get("rejected") or a.get("protocol"))


def _relation_cell(e: dict, a: dict) -> str:
    if e.get("kind") == "axis":
        return "---"
    rel = a.get("relation")
    if e["status"] == "unmapped":
        return r"\emph{none}" if _argued(a) else "---"
    if rel:
        return tex(rel)
    return r"\emph{auto}"     # harness match not yet confirmed by a curator


def _concept_cell(e: dict, a: dict) -> str:
    st = e["status"]
    if e.get("sty_tui"):  # axis row -> a UMLS semantic TYPE, not a concept
        return (rf"{tex(e.get('sty_name'))} "
                rf"\emph{{(semantic type, tree {tex(e.get('sty_tree'))})}}")
    if e.get("kind") == "axis":
        return r"\emph{no semantic type (boolean / free-text dimension)}"
    if st == "pending":
        return r"\emph{pending --- run harness with a UMLS key}"
    if st == "unmapped":
        if _argued(a):
            n = len(a.get("rejected") or [])
            detail = (rf"{n} rejected near-miss{'es' if n != 1 else ''}"
                      if n else "search protocol recorded")
            return rf"\emph{{no faithful concept; argued gap ({detail})}}"
        return r"\emph{unresolved; no faithful concept found}"
    name = tex(e.get("matched_name"))
    sty = "; ".join(tex(x) for x in (e.get("semantic_types") or []))
    src = tex(e.get("root_source"))
    detail = "; ".join(x for x in (sty, src) if x)
    cell = name
    if detail:
        cell += rf" \emph{{({detail})}}"
    if st == "review":
        cell = r"\textsuperscript{\dag}" + cell
    return cell


def _coverage(doc: dict, adj: dict) -> str:
    """Honest coverage sentence computed from the rows, not hard-coded."""
    entries = doc["entries"]
    axes = [e for e in entries if e.get("kind") == "axis"]
    values = [e for e in entries if e.get("kind") != "axis"]
    typed_axes = [e for e in axes if e.get("sty_tui")]
    untyped_axes = [e for e in axes if not e.get("sty_tui")]
    mapped = [e for e in values if e["status"] == "mapped"]
    review = [e for e in values if e["status"] == "review"]
    unmapped = [e for e in values if e["status"] == "unmapped"]
    argued = [e for e in unmapped if _argued(adj.get(_adj_key(e), {}))]
    unresolved = [e for e in unmapped if e not in argued]
    with_rel = [e for e in mapped if adj.get(_adj_key(e), {}).get("relation")]

    by_dim: dict[str, list[str]] = {}
    for e in argued:
        by_dim.setdefault(e["dimension"], []).append(e["token"])
    gaps = "; ".join(rf"\emph{{{tex(d)}}}: {', '.join(tex(t) for t in ts)}"
                     for d, ts in by_dim.items())

    s1 = (rf"\noindent\textbf{{Coverage.}} The model has {len(axes)} "
          rf"dimension axes; {len(typed_axes)} are bound to a UMLS Semantic "
          rf"Type")
    if untyped_axes:
        s1 += (rf", and {len(untyped_axes)} boolean or free-text dimensions "
               rf"take no type by design")
    s1 += "."
    s2 = (rf" Of the {len(values)} enumerated values, {len(mapped)} carry an "
          rf"accepted mapping")
    if len(with_rel) != len(mapped):
        s2 += rf" ({len(with_rel)} with a curated relation)"
    if review:
        s2 += rf", {len(review)} remain flagged for review"
    if unmapped:
        if argued and not unresolved:
            s2 += (rf" and {len(unmapped)} are argued gaps with a structured "
                   rf"rationale ({gaps})")
        else:
            s2 += rf" and {len(unmapped)} are without a faithful UMLS concept"
            if argued:
                s2 += (rf": {len(argued)} argued gaps with a structured "
                       rf"rationale ({gaps})")
            if unresolved:
                s2 += rf"; {len(unresolved)} unresolved"
    return s1 + s2 + "."


def render_umls(doc: dict, adj: dict) -> list[str]:
    out = [
        r"\subsection{UMLS concept crosswalk (generated)}",
        r"\label{sec:s-umls-crosswalk}",
        "",
        # Purpose and provenance.
        r"This crosswalk binds Genetic Evidence Model dimensions to "
        r"Unified Medical Language System (UMLS) Semantic Types and maps "
        r"enumerated values to UMLS concepts where an adequate mapping "
        r"is available. It is produced by the mapping harness "
        r"(\texttt{gem-umls-crosswalk}), which resolves each term against "
        r"the UMLS Metathesaurus through the UTS REST API or against a "
        r"locally indexed licensed copy, and by curator adjudication in the "
        r"accompanying curation studio (\texttt{gem-mapping-studio}). The "
        r"machine-readable sources are \texttt{data/umls/umls\_crosswalk.yaml} "
        r"(the harness output) and \texttt{data/umls/adjudications.yaml} "
        r"(the curator's decisions). The narrative behind the decisions is "
        r"kept in the repository's \texttt{data/umls/DECISIONS.md}.",
        "",
        # Relation to the standards crosswalk.
        r"This UMLS crosswalk is distinct from the structural standards "
        r"crosswalk in \Cref{sec:supp-crosswalk} and does not replace it.",
        "",
        # Identifier policy.
        r"A concept is reported as mapped only when the harness retrieved it "
        r"and it was confirmed against UMLS. No concept identifier is "
        r"asserted unless it was returned by a query and confirmed "
        r"against UMLS.",
        "",
        # Mapping structure.
        r"Each dimension \emph{axis} is bound to a UMLS Semantic Type. The "
        r"type scopes the search for that dimension's values; a curator may "
        r"deliberately accept a concept outside the axis and records why. "
        r"Each dimension \emph{value} is mapped to a Metathesaurus concept. "
        r"The \emph{relation} column records how the accepted concept "
        r"relates to the GEM token: \emph{exact}, \emph{close}, "
        r"\emph{narrower} (the GEM token is more specific than the concept), "
        r"\emph{broader} (the GEM token is more general), or \emph{related} "
        r"(a constituent or operator concept anchors a composite token).",
        "",
        # Argued gaps.
        r"An unmapped value is an adjudicated conclusion, not an absence. "
        r"Relation \emph{none} means that no faithful UMLS mapping was "
        r"accepted. The verdict is supported by rejected near-miss "
        r"concepts, each assigned the adequacy criterion it failed, and by "
        r"the documented search protocol that found no proxy. Where a "
        r"concept identifier appears in connection with an argued gap, it "
        r"identifies a retrieved or rejected near miss, not an accepted "
        r"mapping. The credibility tiers are argued in full in "
        r"\Cref{sec:supp-credibility}.",
        "",
        _coverage(doc, adj),
        "",
    ]
    if not doc["meta"].get("live", False):
        out += [r"\noindent\emph{This table was generated in scaffold mode "
                r"(no UMLS key); concept columns are pending until the harness "
                r"is run against UMLS.}", ""]

    header = r"GEM value & CUI / TUI & Relation & UMLS concept or semantic type \\"
    out += [
        r"{\footnotesize",
        r"\begin{longtable}{@{}l l l p{7.2cm}@{}}",
        r"\caption{GEM dimensional vocabulary mapped to UMLS concepts "
        r"(generated by the mapping harness and curator adjudication).}\\",
        r"\toprule", header, r"\midrule", r"\endfirsthead",
        r"\toprule", header, r"\midrule", r"\endhead",
    ]
    # group by dimension, preserving inventory order
    cur = None
    for e in doc["entries"]:
        if e["dimension"] != cur:
            cur = e["dimension"]
            out.append(rf"\midrule \multicolumn{{4}}{{@{{}}l}}"
                       rf"{{\textbf{{{tex(cur)}}}}} \\")
        a = adj.get(_adj_key(e), {}) or {}
        label = "(axis)" if e["kind"] == "axis" else tex(e["token"])
        ident = tex(e.get("sty_tui")) if e.get("sty_tui") else (
            tex(e.get("cui")) if e.get("cui") else "---")
        out.append(rf"\quad {label} & {ident} & {_relation_cell(e, a)} & "
                   rf"{_concept_cell(e, a)} \\")
    out += [r"\bottomrule", r"\end{longtable}", r"}", ""]
    return out


def render_omop(omop: dict) -> list[str]:
    out = [
        r"\subsection{OMOP CDM positioning (illustrative)}",
        r"\label{sec:s-omop-positioning}",
        "",
        r"The following worked examples position GEM dimensions relative to "
        r"the OHDSI OMOP Common Data Model (CDM) and its standardised "
        r"vocabularies. This is an illustrative, hand-authored positioning "
        r"exercise, not a full crosswalk. " + tex(omop["meta"]["note"]),
        "",
        r"{\footnotesize",
        r"\begin{longtable}{@{}p{2.9cm} p{2.6cm} p{2.1cm} p{6.0cm}@{}}",
        r"\caption{Illustrative positioning of GEM dimensions against the "
        r"OMOP CDM (hand-authored, not exhaustive).}\\",
        r"\toprule",
        r"GEM dimension & OMOP domain / table & Standard vocab. & "
        r"Alignment and gap \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"GEM dimension & OMOP domain / table & Standard vocab. & "
        r"Alignment and gap \\",
        r"\midrule",
        r"\endhead",
    ]
    # Marker convention for hand-authored YAML text: [[supp-crosswalk]]
    # becomes a \Cref to the standards crosswalk note (raw LaTeX cannot pass
    # through the escaper).
    refs = {"[[supp-crosswalk]]": r"\Cref{sec:supp-crosswalk}"}
    for ex in omop["examples"]:
        domain = tex(ex["omop_domain"]) + r"\newline " + tex(ex["omop_table"])
        cell = tex(ex["alignment"]) + r" \emph{Gap:} " + tex(ex["gap"])
        for k, v in refs.items():
            cell = cell.replace(k, v)
        out.append(rf"{tex(ex['gem_dimension'])} & {domain} & "
                   rf"{tex(ex['standard_vocabulary'])} & {cell} \\")
        out.append(r"\addlinespace")
    out += [r"\bottomrule", r"\end{longtable}", r"}", ""]
    return out


def render(crosswalk_path: Path, omop_path: Path,
           adjudications_path: Path | None = None) -> str:
    """Render the section. ``adjudications_path`` defaults to the workspace's
    current adjudications file (``build_umls_crosswalk.ADJUDICATIONS``); a
    missing file simply yields no relation/rationale overlay."""
    doc = yaml.safe_load(crosswalk_path.read_text())
    omop = yaml.safe_load(omop_path.read_text())
    adj = H.load_adjudications(adjudications_path)
    lines = [
        r"% =====================================================================",
        r"%  GENERATED by gem-umls-render (forome.gem.umls.render_crosswalk_tex)",
        r"%  -- do not edit by hand. Sources: data/umls/umls_crosswalk.yaml,",
        r"%  data/umls/adjudications.yaml, data/umls/omop_cdm_examples.yaml.",
        r"%  Requires: \usepackage{longtable} and \usepackage{booktabs}.",
        r"%  Its own supplement section; it does not touch s15_crosswalk.tex.",
        r"% =====================================================================",
        r"\section{UMLS crosswalk and illustrative OMOP CDM positioning}",
        r"\label{sec:s-umls-omop}",
        "",
    ]
    lines += render_umls(doc, adj)
    lines += render_omop(omop)
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crosswalk", default=str(DEFAULT_CROSSWALK))
    ap.add_argument("--omop", default=str(DEFAULT_OMOP))
    ap.add_argument("--adjudications", default=None,
                    help="curator decisions YAML (default: the workspace's "
                         "data/umls/adjudications.yaml)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    out = render(Path(args.crosswalk), Path(args.omop),
                 Path(args.adjudications) if args.adjudications else None)
    Path(args.out).write_text(out)
    print(f"Wrote {args.out} ({len(out)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
