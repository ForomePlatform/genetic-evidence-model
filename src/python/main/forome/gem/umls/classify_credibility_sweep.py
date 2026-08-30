#!/usr/bin/env python3
"""Classify the credibility-sweep candidates against the adequacy criteria.

Applies the rule families (regular expressions over the concept's preferred
name) that assign each candidate the criterion it fails -- A denotation,
B granularity, C set membership, D domain sense -- with a one-line reason.
Together with ``gem-umls-sweep`` and ``data/umls/sweeps/credibility.yaml``
this fully regenerates the curated results from any licensed UMLS copy; the
results themselves are not redistributed (they carry UMLS-derived strings).

Usage:
    gem-umls-classify-credibility RESULTS.yaml [--check]

``--check`` reports the classification without writing. A candidate no rule
matches is left unclassified (``fails: null``) and reported -- extend RULES
rather than forcing a code.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter

import yaml

# (criterion, regex on the preferred name, one-line reason). Order matters:
# specific families come before generic degree words.
RULES: list[tuple[str, str, str]] = [
 ("C", r"^(Definite|Probable|Possible|Probably|Possibly|Definitely|Unlikely|Certain)(\s*\(.*\))?$|^(Probable|Possible|Definite) diagnosis$",
  "epistemic-modality qualifier (SNOMED diagnostic-certainty family: definite/probable/possible) — the nearest UMLS construct; denotes the likelihood that a proposition holds, not the defeasibility of trust in an evidence item; a three-point ladder with no intensified top, bound in its sources to diagnosis assertions (also D)"),
 ("D", r"Related to Intervention",
  "adverse-event causality attribution ladder (NCI: definitely/probably/possibly related) — degree of belief about causation of one event, not warrant for a research finding"),
 ("D", r"TNM|degree of certainty of|Qualifier for TNM",
  "SNOMED/TNM certainty factor (C-factor): certainty of a staging classification for one patient, a diagnostic-assertion qualifier, not evidence credibility"),
 ("D", r"Level of Diagnostic Certainty|Diagnosis Confidence Level|UHDRS",
  "certainty of a clinical diagnosis (rating-scale item), not warrant for a research finding (also B: names the dimension, not a level)"),
 ("D", r"Level of evidence.*(Bld|Tiss|Molecular|Blood)",
  "LOINC molecular-pathology 'level of evidence' (AMP/ASCO/CAP actionability tier for a variant's clinical significance): a clinical-actionability tier bound to a variant report, not curator warrant for an evidence item (also B: the attribute, not a level)"),
 ("D", r"Metabolite Identification Confidence",
  "metabolomics identification-confidence levels (Schymanski 1–5): an ordered epistemic ladder, but about confidence in a structure identification — domain-bound (D) and defined by analytical evidence type, not defeasibility"),
 ("D", r"^Current level of confidence I can|^Current level of confidence|confidence:Find:Pt|Overall level of confidence with|I am confident|How confident|confident (that|about|in)|self[- ]?efficacy",
  "patient-reported self-efficacy questionnaire item (LOINC/PROMIS): confidence in performing an activity, not warrant about evidence"),
 ("D", r"^(Very High|High|Moderate|Low) Confidence$|^(Very |Somewhat |Not at all |Extremely |Fairly |Quite |Slightly )?Confident$|^Not Confident",
  "NCI Clinical or Research Assessment Answer — a questionnaire response option for a respondent's confidence (Female Sexual Function Index subset), not an epistemic grade of evidence, despite matching GEM's four-level shape"),
 ("D", r"self[- ]?esteem|Self Confidence|^Confidence$|Lack of confidence|Loss of confidence|confidence in (self|abilities)|Euphoric",
  "psychological trait/state, not warrant about evidence"),
 ("A", r"^Level of Evidence( (I|II|III|IV|V)[A-Za-z0-9]*)?$|Level of Evidence [IVX]+|^Evidence Level|^Level of evidence$",
  "NCI/PDQ level-of-evidence: a study-design hierarchy (RCT > cohort > case series), not degree of warrant; mapping to it would collapse GEM's method facet into credibility (also C for the GEM scale)"),
 ("A", r"Level of Confidence \(statistical\)|confidence interval|confidence limit|confidence coefficient|^Statistical",
  "statistical quantity (interval/coefficient), not a degree of belief in evidence"),
 ("A", r"probability|likelihood|risk score|risk category|score$|Score\b|Scale$|Index$|staging category",
  "a quantitative score/probability or risk/staging category of a clinical measurand, not epistemic warrant"),
 ("D", r"[Gg]rade|GRADE",
  "'grade' in a non-epistemic sense (tumour, school, product grade)"),
 ("D", r"[Cc]redib",
  "credibility of a health-information source or witness as perceived by a patient/clinician (LOINC/CHV/NIC), not the curator's warrant for an evidence item"),
 ("D", r"\[X\]|alcohol|[Ee]vidence of|evidence-based practice",
  "clinical 'evidence of <condition>' sense (presence of a sign) or a care activity, not evidence strength"),
 ("A", r"^(High|Very high|Very High|Extremely high|Abnormally high|Highest|Low|Very low|Lowest|Moderate|\(\+\) Moderate|Medium|Minimal|Maximal|Maximum|Minimum|Mild|Moderation|Strong|Weak|Weakness|Markedly increased|Increased|Decreased|Normal|Intermediate)(\s*\(.*\))?$",
  "generic degree/qualifier value (SNOMED qualifier-value branch, IS-A Increased/Decreased): magnitude of a measurand, not epistemic degree"),
 ("A", r"^(A )?(Medium|High|Low|Very high|Very low|Moderate|Minimal|Strong|Weak)( Amount| Level| Degree| Dose| Intensity| Frequency| Quality| Risk| Grade| Priority| Severity| Strength| Concentration| Pressure| Temperature| Volume| Density| Power| Speed| Altitude| Titer)?( of .*)?$",
  "degree of a measured/graded property, not warrant about evidence"),
 ("D", r"[Mm]edia\b|Tunica|Lowing|Lower \(action\)|spatial qualifier|Body Site Modifier|Culture Media",
  "lexical collision (medium/media, lower) — unrelated sense"),
 ("A", r"\b(high|low|moderate|medium|very high|very low|minimal|strong|weak|extremely high|highest|mild|maximal)\b",
  "the qualifier appears as a magnitude/degree of a clinical or physical property (measurand degree), not as a degree of epistemic warrant"),
]


def classify(name: str) -> tuple[str, str] | None:
    for code, rx, why in RULES:
        if re.search(rx, name or "", re.I):
            return code, why
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gem-umls-classify-credibility",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("results", help="a gem-umls-sweep results YAML to classify")
    ap.add_argument("--check", action="store_true",
                    help="report only; do not write")
    args = ap.parse_args(argv)
    doc = yaml.safe_load(open(args.results))
    dist: Counter = Counter()
    residual = []
    for c in doc.get("candidates") or []:
        hit = classify(c.get("name"))
        if hit is None:
            residual.append(c)
            continue
        c["fails"], c["why"] = hit
        dist[hit[0]] += 1
    print(f"classified {sum(dist.values())} of "
          f"{len(doc.get('candidates') or [])}: {dict(dist)}")
    for c in residual:
        print(f"  UNCLASSIFIED {c.get('cui')} {c.get('name')!r} "
              f"{c.get('root_source')}")
    if residual:
        print("extend RULES for the unclassified candidates; nothing written"
              if not args.check else "")
        return 1
    if not args.check:
        yaml.safe_dump(doc, open(args.results, "w"), sort_keys=False,
                       allow_unicode=True, width=110)
        print(f"written: {args.results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
