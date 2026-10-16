#!/usr/bin/env python3
"""Execute the typical-stratum draw recorded in study/PAPERS.md Section 1.5.

The script mechanises everything except the intake judgment itself: it
derives the deterministic candidate order (seed 0, per-group shuffles,
citation strata, fallbacks), presents one candidate at a time, validates
that outcomes are recorded in slot order, appends each outcome to
study/draw_log.csv, and regenerates the draw record in Section 1.9 of
study/PAPERS.md. State is never stored: it is replayed from the frame and
the log on every run, so a log inconsistent with the recorded procedure is
refused outright.

Usage (from anywhere; paths are resolved relative to the repository):
  scripts/study_draw.py status              show the slot board
  scripts/study_draw.py next                show the candidate awaiting intake
  scripts/study_draw.py record PMID pass [-r "notes"]
  scripts/study_draw.py record PMID fail -r "criterion 3: only one claim"
  scripts/study_draw.py list [SLOT] [-n N]  audit a slot's candidate order
  scripts/study_draw.py sync                regenerate Section 1.9 only

Use --typical 9 or 10 to open the pre-specified extension slots; the flag
may be given before or after the subcommand.
"""

import argparse
import csv
import datetime
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = "0"
SNAP = datetime.date(2026, 10, 15)

GROUPS = {
    "Am J Hum Genet": "A", "Eur J Hum Genet": "A", "Hum Genet": "A",
    "J Med Genet": "A", "Genet Med": "A", "Clin Genet": "A",
    "Mol Genet Genomic Med": "A", "Nat Genet": "A",
    "Genet Epidemiol": "B", "Ann Hum Genet": "B", "HGG Adv": "B",
    "NPJ Genom Med": "B", "Hum Genomics": "B", "BMC Med Genomics": "B",
    "Hum Mol Genet": "C", "PLoS Genet": "C", "Genome Biol": "C",
    "BMC Genomics": "D", "BMC Genom Data": "D",
    "Nature": "E", "Science": "E", "Proc Natl Acad Sci U S A": "E",
    "Cell": "E", "Blood": "E",
    "PLoS Comput Biol": "F", "Bioinformatics": "F", "Brief Bioinform": "F",
    "BMC Bioinformatics": "F", "NAR Genom Bioinform": "F",
    "GigaScience": "F", "Genome Res": "F", "Genome Med": "F",
}

BASE_SLOTS = [
    ("A1", "A", "WELL"), ("A2", "A", "FREE"),
    ("B1", "B", "WELL"), ("B2", "B", "ZERO"),
    ("C1", "C", "WELL"), ("D1", "D", "ZERO"),
    ("E1", "E", "WELL"), ("F1", "F", "FREE"),
]
EXT_SLOTS = [("C2", "C", "WELL"), ("A3", "A", "ZERO")]
ALL_SLOTS = BASE_SLOTS + EXT_SLOTS
COLLAPSE = {"E": "A", "F": "C", "D": "C"}

FRAME_COLS = ["pmid", "pmcid", "doi", "journal", "pubdate", "epubdate",
              "earliest_date", "excluded_reason", "citedby_epmc_20261015",
              "title"]
LOG_COLS = ["date", "slot", "pmid", "result", "reasons", "minutes"]
MARK_BEGIN = "<!-- draw-record:begin -->"
MARK_END = "<!-- draw-record:end -->"

INTAKE_CHECKLIST = """\
Intake screen (protocol Section 6.4); record whether the paper:
  1. is a primary research article in English;
  2. can be extracted into usable canonical text;
  3. contains at least two separate claims linking a genetic entity to a
     phenotype;
  4. is in scope, or is deliberately adjacent to GEM's current scope;
  5. has low, medium, or high expected candidate-extension load;
  6. belongs in the typical or stress stratum;
  7. was published before or after the documented model training cutoff;
  8. is likely to be unusually familiar to the model because it is
     prominent, highly cited, or heavily curated.
No paper from the original six-paper corpus is eligible because those
papers were used in annotator training and, for four papers, as AI
exemplars."""


def die(msg):
    sys.exit(f"study_draw: error: {msg}")


def load_frame(path):
    """Return {pmid:int -> row dict} for eligible rows, with derived fields."""
    try:
        f = open(path, encoding="utf-8")
    except OSError as e:
        die(f"cannot read frame: {e}")
    frame = {}
    with f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FRAME_COLS:
            die(f"unexpected frame columns in {path}: {reader.fieldnames}")
        for r in reader:
            # eligibility matches the Section 1.5 command: plain truthiness
            if r["excluded_reason"]:
                continue
            if r["journal"] not in GROUPS:
                die(f"journal not in the recorded venue set: {r['journal']!r}")
            pmid = int(r["pmid"])
            if pmid in frame:
                die(f"duplicate PMID in frame: {pmid}")
            r["group"] = GROUPS[r["journal"]]
            r["cites"] = int(r["citedby_epmc_20261015"] or 0)
            d = datetime.date.fromisoformat(r["earliest_date"])
            r["age_days"] = (SNAP - d).days
            frame[pmid] = r
    if not frame:
        die("no eligible rows in frame")
    return frame


def build_orders(frame):
    """Seeded shuffles per Section 1.5: one stream per group, plus ALL."""
    orders = {}
    for g in "ABCDEF":
        pool = sorted(p for p, r in frame.items() if r["group"] == g)
        random.Random(f"{SEED}:{g}").shuffle(pool)
        orders[g] = pool
    pool = sorted(frame)
    random.Random(f"{SEED}:ALL").shuffle(pool)
    orders["ALL"] = pool
    return orders


def in_stratum(row, stratum):
    if stratum == "WELL":
        return row["cites"] >= 2
    if stratum == "ZERO":
        return row["cites"] == 0 and row["age_days"] >= 183
    return True  # FREE


def phases_for(slot):
    """Candidate phases in fallback order (Section 1.5 fallback bullet)."""
    _, group, stratum = slot
    phases = [(group, stratum)]
    if stratum != "FREE":
        phases.append((group, "FREE"))
    if group in COLLAPSE:
        phases.append((COLLAPSE[group], "FREE"))
    phases.append(("ALL", "FREE"))
    return phases


def phase_label(slot, phase):
    _, group, stratum = slot
    g, s = phase
    if (g, s) == (group, stratum):
        return f"primary ({stratum} in group {group})"
    if g == group:
        return f"stratum fallback ({stratum} exhausted; FREE in group {group})"
    if g == "ALL":
        return "simple-random fallback over all remaining eligible rows"
    return f"group fallback (group {group} exhausted; collapsed into {g})"


def next_candidate(slot, frame, orders, decided):
    """First undecided paper in the slot's phased walk, with its phase.

    Deliberately keeps no memory across phases: a paper passed over in an
    earlier phase only for a stratum mismatch must stay reachable in the
    laxer fallback phases (Section 1.5 fallback order). Only `decided`
    removes a paper.
    """
    for phase in phases_for(slot):
        g, s = phase
        for pmid in orders[g]:
            if pmid in decided:
                continue
            if in_stratum(frame[pmid], s):
                return pmid, phase
    return None, None


def read_log(path):
    if not Path(path).exists():
        return []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, restkey="__extra__")
        if reader.fieldnames is None:
            die(f"log file {path} is empty; delete it or restore the "
                f"header line: {','.join(LOG_COLS)}")
        if reader.fieldnames != LOG_COLS:
            die(f"unexpected log columns in {path}: {reader.fieldnames}")
        return list(reader)


def replay(log_rows, frame, orders):
    """Validate the log against the procedure and return the derived state.

    Returns (entries, filled, decided, slot_idx) where entries carries one
    audited dict per log row (with its derived phase), filled maps slot
    name to the passing PMID, decided maps PMID to (slot, result), and
    slot_idx indexes the first unfilled slot in ALL_SLOTS.
    """
    entries = []
    filled = {}
    decided = {}
    slot_idx = 0
    for n, row in enumerate(log_rows, 1):  # data rows, header excluded
        if slot_idx >= len(ALL_SLOTS):
            die(f"log row {n}: all {len(ALL_SLOTS)} slots already filled")
        if "__extra__" in row:
            die(f"log row {n}: too many fields; repair the log by hand")
        if any(row.get(c) is None for c in LOG_COLS):
            die(f"log row {n}: too few fields; repair the log by hand")
        if MARK_BEGIN in row["reasons"] or MARK_END in row["reasons"]:
            die(f"log row {n}: reasons must not contain the draw-record "
                f"marker text")
        try:
            datetime.date.fromisoformat(row["date"])
        except ValueError:
            die(f"log row {n}: date {row['date']!r} is not an ISO date")
        slot = ALL_SLOTS[slot_idx]
        expected, phase = next_candidate(slot, frame, orders, decided)
        if expected is None:
            die(f"log row {n}: frame exhausted for slot {slot[0]}")
        if row["slot"] != slot[0]:
            die(f"log row {n}: expected slot {slot[0]}, found {row['slot']!r}")
        pm = row["pmid"]
        if not (pm.isascii() and pm.isdigit()) or int(pm) != expected:
            die(f"log row {n}: expected candidate PMID {expected} for slot "
                f"{slot[0]}, found {row['pmid']!r}; the log does not match "
                f"the recorded procedure")
        if row["result"] not in ("pass", "fail"):
            die(f"log row {n}: result must be pass or fail, "
                f"found {row['result']!r}")
        if row["result"] == "fail" and not row["reasons"].strip():
            die(f"log row {n}: a fail must record reasons")
        m = row["minutes"].strip()
        if m and not (m.isascii() and m.isdigit()):
            die(f"log row {n}: minutes must be a whole number or empty, "
                f"found {row['minutes']!r}")
        pmid = int(row["pmid"])
        decided[pmid] = (slot[0], row["result"])
        entries.append({**row, "pmid": pmid, "phase": phase_label(slot, phase)})
        if row["result"] == "pass":
            filled[slot[0]] = pmid
            slot_idx += 1
    return entries, filled, decided, slot_idx


def candidate_block(frame, pmid, slot, phase):
    r = frame[pmid]
    lines = [
        f"Slot {slot[0]} (group {slot[1]}, stratum {slot[2]}); "
        f"phase: {phase_label(slot, phase)}",
        f"  PMID        {pmid}",
        f"  Title       {r['title']}",
        f"  Journal     {r['journal']} (group {r['group']})",
        f"  Dates       pubdate {r['pubdate']!r}, epubdate {r['epubdate']!r}, "
        f"earliest {r['earliest_date']} ({r['age_days']} days at snapshot)",
        f"  Citations   {r['cites']} (column citedby_epmc_20261015)",
        f"  DOI         https://doi.org/{r['doi']}" if r["doi"] else
        "  DOI         (none recorded)",
        f"  PubMed      https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        f"  Europe PMC  https://europepmc.org/article/MED/{pmid}",
    ]
    if r["pmcid"]:
        lines.append(f"  Full text   https://www.ebi.ac.uk/europepmc/"
                     f"webservices/rest/{r['pmcid']}/fullTextXML")
    return "\n".join(lines)


def md_escape(text):
    return text.replace("|", "\\|").replace("\n", " ").strip()


def render_record(entries, filled, slot_idx, typical):
    lines = [
        MARK_BEGIN,
        "",
        f"Screening is performed by the human annotator in the intake "
        f"web page (operating instructions: `docs/DRAW_SOP.md`). "
        f"Synchronised outcomes live in `study/draw_log.csv` and are "
        f"revalidated by `scripts/study_draw.py` (seed {SEED}, snapshot "
        f"column `citedby_epmc_20261015`), which regenerates this "
        f"block; do not edit it by hand.",
        "",
    ]
    if not entries:
        lines.append("No draws recorded yet.")
    else:
        lines.append("| # | Date | Slot | Phase | PMID | Journal | Result "
                     "| Reasons | Minutes |")
        lines.append("| ---: | --- | --- | --- | --- | --- | --- | --- "
                     "| ---: |")
        for i, e in enumerate(entries, 1):
            lines.append(
                f"| {i} | {md_escape(e['date'])} | {e['slot']} "
                f"| {md_escape(e['phase'])} | {e['pmid']} "
                f"| {md_escape(e['journal'])} | {e['result']} "
                f"| {md_escape(e['reasons'])} | {md_escape(e['minutes'])} |")
        lines.append("")
        done = ", ".join(f"{s}={p}" for s, p in filled.items())
        lines.append(f"Slots filled: {done if done else 'none'}.")
    if slot_idx >= typical:
        lines.append(f"The draw is complete for {typical} typical papers.")
    else:
        lines.append(f"Current slot: {ALL_SLOTS[slot_idx][0]} "
                     f"({slot_idx} of {typical} slots filled).")
    lines += ["", MARK_END]
    return "\n".join(lines)


def read_papers(papers_path):
    """Read PAPERS.md and validate the draw-record marker pair."""
    try:
        text = Path(papers_path).read_text(encoding="utf-8")
    except OSError as e:
        die(f"cannot read {papers_path}: {e}")
    if text.count(MARK_BEGIN) != 1 or text.count(MARK_END) != 1:
        die(f"{papers_path} must contain exactly one draw-record marker "
            f"pair ({MARK_BEGIN} ... {MARK_END})")
    if text.find(MARK_END) < text.find(MARK_BEGIN):
        die(f"draw-record END marker precedes BEGIN marker in {papers_path}")
    return text


def sync_papers(papers_path, entries, filled, slot_idx, typical):
    text = read_papers(papers_path)
    head, rest = text.split(MARK_BEGIN, 1)
    _, tail = rest.split(MARK_END, 1)
    block = render_record(entries, filled, slot_idx, typical)
    out = head + block + tail
    if out.count(MARK_BEGIN) != 1 or out.count(MARK_END) != 1:
        die("regenerated draw record would duplicate the markers; a "
            "recorded field must not contain marker text")
    # open() rather than Path.write_text(newline=...): the latter needs
    # Python 3.10, and this script must run on a stock macOS python3
    with open(papers_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)


def append_log(log_path, row):
    p = Path(log_path)
    fresh = not p.exists() or p.stat().st_size == 0
    if not fresh:
        # a log whose last line lost its newline would silently merge
        # rows; replay has already validated the content this run, so
        # restoring the terminator is safe
        with open(log_path, "rb+") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                f.write(b"\n")
    with open(log_path, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS, lineterminator="\n")
        if fresh:
            w.writeheader()
        w.writerow(row)


def enrich(entries, frame):
    for e in entries:
        e["journal"] = frame[e["pmid"]]["journal"]
    return entries


def cmd_status(args, frame, orders, state):
    entries, filled, decided, slot_idx = state
    n_fail = sum(1 for _, res in decided.values() if res == "fail")
    print(f"Frame: {len(frame)} eligible papers. Outcomes recorded: "
          f"{len(decided)} ({len(filled)} pass, {n_fail} fail). "
          f"Typical papers this run: {args.typical}.")
    for i, slot in enumerate(ALL_SLOTS):
        name, group, stratum = slot
        if i >= args.typical:
            if name in filled:
                print(f"  {name} [{group}/{stratum}]  FILLED beyond "
                      f"--typical {args.typical}: PMID {filled[name]}")
            continue
        if name in filled:
            pmid = filled[name]
            print(f"  {name} [{group}/{stratum}]  filled: PMID {pmid}, "
                  f"{frame[pmid]['journal']}")
        elif i == slot_idx:
            pmid, phase = next_candidate(slot, frame, orders, decided)
            if pmid is None:
                print(f"  {name} [{group}/{stratum}]  CURRENT, frame "
                      f"exhausted")
            else:
                print(f"  {name} [{group}/{stratum}]  CURRENT; awaiting "
                      f"intake: PMID {pmid} "
                      f"({phase_label(slot, phase)})")
        else:
            print(f"  {name} [{group}/{stratum}]  queued")
    if slot_idx >= args.typical:
        print(f"The draw is complete for {args.typical} typical papers.")


def cmd_next(args, frame, orders, state):
    entries, filled, decided, slot_idx = state
    if slot_idx >= args.typical:
        print(f"The draw is complete for {args.typical} typical papers. "
              f"Use --typical 9 or 10 to open the extension slots.")
        return
    slot = ALL_SLOTS[slot_idx]
    pmid, phase = next_candidate(slot, frame, orders, decided)
    if pmid is None:
        die(f"frame exhausted for slot {slot[0]}")
    print(candidate_block(frame, pmid, slot, phase))
    print()
    print(INTAKE_CHECKLIST)
    print()
    print(f"Record with: scripts/study_draw.py record {pmid} pass|fail "
          f"-r \"reasons\"")


def cmd_record(args, frame, orders, state, paths):
    entries, filled, decided, slot_idx = state
    if slot_idx >= args.typical:
        die(f"the draw is complete for {args.typical} typical papers; "
            f"use --typical 9 or 10 for the extension slots")
    slot = ALL_SLOTS[slot_idx]
    expected, phase = next_candidate(slot, frame, orders, decided)
    if expected is None:
        die(f"frame exhausted for slot {slot[0]}")
    if not (args.pmid.isascii() and args.pmid.isdigit()) \
            or int(args.pmid) != expected:
        die(f"PMID {args.pmid} is not the candidate awaiting intake; "
            f"slot {slot[0]} awaits PMID {expected} (run 'next' to see it)")
    if args.result == "fail" and not (args.reasons or "").strip():
        die("a fail must record reasons: -r \"criterion N: ...\"")
    reasons = (args.reasons or "").strip()
    if MARK_BEGIN in reasons or MARK_END in reasons:
        die("reasons must not contain the draw-record marker text")
    if args.result == "pass" and not reasons:
        reasons = "all intake criteria met"
    minutes = (args.minutes or "").strip()
    if minutes and not (minutes.isascii() and minutes.isdigit()):
        die("minutes must be a whole number")
    read_papers(paths["papers"])  # validate markers before touching the log
    row = {"date": datetime.date.today().isoformat(), "slot": slot[0],
           "pmid": str(expected), "result": args.result, "reasons": reasons,
           "minutes": minutes}
    append_log(paths["log"], row)
    state = replay(read_log(paths["log"]), frame, orders)
    entries, filled, decided, slot_idx = state
    sync_papers(paths["papers"], enrich(entries, frame), filled, slot_idx,
                args.typical)
    r = frame[expected]
    print(f"Recorded: slot {slot[0]}, PMID {expected} ({r['journal']}), "
          f"{args.result}: {reasons}")
    if args.result == "pass":
        print(f"Slot {slot[0]} is filled.")
    if slot_idx >= args.typical:
        print(f"The draw is complete for {args.typical} typical papers.")
    else:
        nxt = ALL_SLOTS[slot_idx]
        pmid, phase = next_candidate(nxt, frame, orders, decided)
        if pmid is None:
            print(f"Next: slot {nxt[0]}, but the frame is exhausted for it.")
        else:
            print(f"Next: slot {nxt[0]} awaits PMID {pmid} "
                  f"({phase_label(nxt, phase)}). Run 'next' for details.")


def cmd_list(args, frame, orders, state):
    entries, filled, decided, slot_idx = state
    slots = [s for s in ALL_SLOTS if s[0] == args.slot] if args.slot \
        else [ALL_SLOTS[min(slot_idx, len(ALL_SLOTS) - 1)]]
    if not slots:
        die(f"unknown slot {args.slot!r}; slots: "
            + ", ".join(s[0] for s in ALL_SLOTS))
    slot = slots[0]
    print(f"Candidate order for slot {slot[0]} (group {slot[1]}, stratum "
          f"{slot[2]}), skipping already decided papers:")
    shown = 0
    seen = set()  # dedupes DISPLAY only: a paper is listed at its first
    # offering phase; it must stay reachable in laxer phases (see
    # next_candidate), so it is marked seen only once printed
    for phase in phases_for(slot):
        g, s = phase
        for pmid in orders[g]:
            if shown >= args.n:
                return
            if pmid in seen or pmid in decided:
                continue
            if not in_stratum(frame[pmid], s):
                continue
            seen.add(pmid)
            r = frame[pmid]
            print(f"  {shown + 1:3d}. {pmid}  [{phase_label(slot, phase)}]"
                  f"  {r['journal']}: {r['title'][:70]}")
            shown += 1
    if shown == 0:
        print("  (frame exhausted for this slot)")


def cmd_sync(args, frame, orders, state, paths):
    entries, filled, decided, slot_idx = state
    sync_papers(paths["papers"], enrich(entries, frame), filled, slot_idx,
                args.typical)
    print(f"Section 1.9 of {paths['papers']} regenerated "
          f"({len(entries)} recorded outcomes).")


def add_shared(parser, suppress):
    """Shared options; subcommands take them too (defaults on main only)."""
    d = argparse.SUPPRESS if suppress else None
    parser.add_argument("--typical", type=int, choices=(8, 9, 10),
                        default=d if suppress else 8,
                        help="number of typical papers (default 8; 9 and "
                             "10 open the pre-specified extension slots)")
    parser.add_argument("--frame",
                        default=d if suppress
                        else str(ROOT / "study/papers_frame.csv"))
    parser.add_argument("--log",
                        default=d if suppress
                        else str(ROOT / "study/draw_log.csv"))
    parser.add_argument("--papers",
                        default=d if suppress
                        else str(ROOT / "study/PAPERS.md"))


def main():
    ap = argparse.ArgumentParser(
        description="Run the recorded typical-stratum draw "
                    "(study/PAPERS.md Section 1.5).")
    add_shared(ap, suppress=False)
    shared = argparse.ArgumentParser(add_help=False)
    add_shared(shared, suppress=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", parents=[shared])
    sub.add_parser("next", parents=[shared])
    p = sub.add_parser("record", parents=[shared])
    p.add_argument("pmid")
    p.add_argument("result", choices=("pass", "fail"))
    p.add_argument("-r", "--reasons", default="")
    p.add_argument("-m", "--minutes", default="",
                   help="screening time in whole minutes (intake effort)")
    p = sub.add_parser("list", parents=[shared])
    p.add_argument("slot", nargs="?")
    p.add_argument("-n", type=int, default=15)
    sub.add_parser("sync", parents=[shared])
    args = ap.parse_args()

    frame = load_frame(args.frame)
    orders = build_orders(frame)
    state = replay(read_log(args.log), frame, orders)
    paths = {"log": args.log, "papers": args.papers}

    if args.cmd == "status":
        cmd_status(args, frame, orders, state)
    elif args.cmd == "next":
        cmd_next(args, frame, orders, state)
    elif args.cmd == "record":
        cmd_record(args, frame, orders, state, paths)
    elif args.cmd == "list":
        cmd_list(args, frame, orders, state)
    elif args.cmd == "sync":
        cmd_sync(args, frame, orders, state, paths)


if __name__ == "__main__":
    main()
