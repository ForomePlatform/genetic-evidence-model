#!/usr/bin/env python3
"""Render the UMLS + OMOP/CDM crosswalk as a LaTeX supplement section.

Reads the harness output (``mapping/umls_crosswalk.yaml``) and the
hand-authored OMOP examples (``mapping/omop_cdm_examples.yaml``) and writes a
self-contained ``.tex`` section: an honest UMLS concept table (grouped by
dimension, with mapped / review / unmapped / pending status surfaced) plus an
illustrative OMOP/CDM positioning table.

This produces a NEW supplement section; it does not modify the existing
``s15_crosswalk.tex`` (the SO/HPO/NCBITaxon/ECO/SEPIO/GA4GH-VA/FHIR crosswalk).
The generated file uses ``longtable`` and ``booktabs``; add
``\\usepackage{longtable}`` to the preamble and ``\\input`` it from
``supplement.tex`` when you are ready to wire it into the build.

Usage:
    python3 mapping/render_crosswalk_tex.py
    python3 mapping/render_crosswalk_tex.py --crosswalk mapping/umls_crosswalk.demo.yaml \
        --out mapping/s18_umls_crosswalk.preview.tex
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

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


def _concept_cell(e: dict) -> str:
    st = e["status"]
    if e.get("sty_tui"):  # axis row -> a UMLS semantic TYPE, not a concept
        return (rf"{tex(e.get('sty_name'))} "
                rf"\emph{{(semantic type, tree {tex(e.get('sty_tree'))})}}")
    if st == "pending":
        return r"\emph{pending --- run harness with a UMLS key}"
    if st == "unmapped":
        return r"\emph{no faithful UMLS concept}"
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


def render_umls(doc: dict) -> list[str]:
    out = [
        r"\subsection{UMLS concept crosswalk (generated)}",
        r"\label{sec:s-umls-crosswalk}",
        "",
        r"This crosswalk maps each Genetic Evidence Model dimension and "
        r"enumerated value to a Unified Medical Language System (UMLS) "
        r"concept. It is produced by the mapping harness "
        r"(\texttt{mapping/build\_umls\_crosswalk.py}), which resolves each "
        r"term against the UMLS Metathesaurus through the UTS REST API; the "
        r"machine-readable result is \texttt{mapping/umls\_crosswalk.yaml}. "
        r"It is distinct from, and does not replace, the structural crosswalk "
        r"in \Cref{sec:s-crosswalk}. Only concepts the harness actually "
        r"resolved are reported as mapped; where the top automated match was "
        r"not faithful, a curator either selected a faithful concept from the "
        r"query's returned candidates (recorded in "
        r"\texttt{mapping/adjudications.yaml}) or recorded that none was "
        r"faithful. No concept identifier is asserted that a query did not "
        r"return; entries with no faithful UMLS concept are reported as such "
        r"rather than forced.",
        "",
    ]
    c = doc["meta"]["counts"]
    out += [
        r"Each dimension \emph{axis} is mapped to a UMLS Semantic Type (which "
        r"then constrains the search for that dimension's values, so axis and "
        r"values are consistent by construction); each dimension \emph{value} "
        r"is mapped to a Metathesaurus concept within that type.",
        "",
        rf"\noindent\textbf{{Coverage.}} Of {doc['meta']['total']} GEM "
        rf"dimension entries, {c['mapped']} are mapped "
        rf"({c.get('axis_typed', 0)} dimension axes to a semantic type; the "
        rf"rest to a concept, {c.get('curated', 0)} by curator adjudication) "
        rf"and {c['unmapped']} have no faithful UMLS mapping---chiefly the "
        rf"ordinal credibility tiers, study-design ascertainment routes, and "
        rf"composite relational tokens, whose granularity the Metathesaurus "
        rf"does not represent."
        + (rf" {c['review']} remain flagged for review." if c['review'] else ""),
        "",
    ]
    if not doc["meta"].get("live", False):
        out += [r"\noindent\emph{This table was generated in scaffold mode "
                r"(no UMLS key); concept columns are pending until the harness "
                r"is run against UMLS.}", ""]

    out += [
        r"{\footnotesize",
        r"\begin{longtable}{@{}l l p{8.2cm}@{}}",
        r"\caption{GEM dimensional vocabulary mapped to UMLS concepts "
        r"(generated by the mapping harness).}\\",
        r"\toprule",
        r"GEM value & CUI / TUI & UMLS concept or semantic type \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"GEM value & CUI / TUI & UMLS concept or semantic type \\",
        r"\midrule",
        r"\endhead",
    ]
    # group by dimension, preserving inventory order
    cur = None
    for e in doc["entries"]:
        if e["dimension"] != cur:
            cur = e["dimension"]
            out.append(rf"\midrule \multicolumn{{3}}{{@{{}}l}}"
                       rf"{{\textbf{{{tex(cur)}}}}} \\")
        label = "(axis)" if e["kind"] == "axis" else tex(e["token"])
        ident = tex(e.get("sty_tui")) if e.get("sty_tui") else (
            tex(e.get("cui")) if e.get("cui") else "---")
        out.append(rf"\quad {label} & {ident} & {_concept_cell(e)} \\")
    out += [r"\bottomrule", r"\end{longtable}", r"}", ""]
    return out


def render_omop(omop: dict) -> list[str]:
    out = [
        r"\subsection{OMOP CDM positioning (illustrative)}",
        r"\label{sec:s-omop-positioning}",
        "",
        r"The following worked examples position GEM dimensions relative to "
        r"the OHDSI OMOP Common Data Model (CDM) and its standardised "
        r"vocabularies. This is deliberately not a full crosswalk: it shows "
        r"the partial alignment that exists and flags what the CDM does not "
        r"natively capture for basic-science genetic evidence. " + tex(
            omop["meta"]["note"]),
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
    for ex in omop["examples"]:
        domain = tex(ex["omop_domain"]) + r"\newline " + tex(ex["omop_table"])
        cell = tex(ex["alignment"]) + r" \emph{Gap:} " + tex(ex["gap"])
        out.append(rf"{tex(ex['gem_dimension'])} & {domain} & "
                   rf"{tex(ex['standard_vocabulary'])} & {cell} \\")
        out.append(r"\addlinespace")
    out += [r"\bottomrule", r"\end{longtable}", r"}", ""]
    return out


def render(crosswalk_path: Path, omop_path: Path) -> str:
    doc = yaml.safe_load(crosswalk_path.read_text())
    omop = yaml.safe_load(omop_path.read_text())
    lines = [
        r"% =====================================================================",
        r"%  GENERATED by mapping/render_crosswalk_tex.py -- do not edit by hand.",
        r"%  Source: mapping/umls_crosswalk.yaml + mapping/omop_cdm_examples.yaml",
        r"%  Requires: \usepackage{longtable} and \usepackage{booktabs}.",
        r"%  This is a NEW supplement section; it does not touch s15_crosswalk.tex.",
        r"% =====================================================================",
        r"\section{UMLS and OMOP/CDM crosswalk}",
        r"\label{sec:s-umls-omop}",
        "",
    ]
    lines += render_umls(doc)
    lines += render_omop(omop)
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crosswalk", default=str(DEFAULT_CROSSWALK))
    ap.add_argument("--omop", default=str(DEFAULT_OMOP))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    out = render(Path(args.crosswalk), Path(args.omop))
    Path(args.out).write_text(out)
    print(f"Wrote {args.out} ({len(out)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
