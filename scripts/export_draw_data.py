#!/usr/bin/env python3
"""Export the deterministic draw data for the intake screening web page.

Imports scripts/study_draw.py (the adopted executor) and serialises, for
every slot, the full phased candidate sequence, each paper listed once at
its first offering phase. The web page then only has to walk a sequence
and skip decided papers, which is provably equivalent to the script's
next_candidate(); this script verifies that equivalence on randomised
decided-sets before writing the export.

Output: scripts/intake_screen/draw_data.json (committed; it is part of
the record of what the screening operator was shown).
"""
import importlib.util
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "study_draw", ROOT / "scripts" / "study_draw.py")
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)

frame = sd.load_frame(str(ROOT / "study" / "papers_frame.csv"))
orders = sd.build_orders(frame)

slots = [{"name": n, "group": g, "stratum": s} for n, g, s in sd.ALL_SLOTS]
seq = {}
phases = {}
for slot in sd.ALL_SLOTS:
    labels = []
    entries = []
    seen = set()
    for pi, phase in enumerate(sd.phases_for(slot)):
        labels.append(sd.phase_label(slot, phase))
        g, s = phase
        for pmid in orders[g]:
            if pmid in seen or not sd.in_stratum(frame[pmid], s):
                continue
            seen.add(pmid)
            entries.append([pmid, pi])
    seq[slot[0]] = entries
    phases[slot[0]] = labels

papers = {str(p): [r["title"], r["journal"], r["group"], r["cites"],
                   r["earliest_date"], r["doi"], r["pmcid"]]
          for p, r in frame.items()}

# equivalence check: first undecided entry of the exported sequence must
# match next_candidate() for randomised decided-sets across all slots
rng = random.Random(12345)
all_pmids = list(frame)
for trial in range(2000):
    decided = set(rng.sample(all_pmids, rng.randrange(0, 80)))
    slot = sd.ALL_SLOTS[rng.randrange(len(sd.ALL_SLOTS))]
    exp_pmid, exp_phase = sd.next_candidate(slot, frame, orders, decided)
    got = next(((p, pi) for p, pi in seq[slot[0]] if p not in decided),
               (None, None))
    assert got[0] == exp_pmid, (slot, exp_pmid, got)
    if exp_pmid is not None:
        assert phases[slot[0]][got[1]] == sd.phase_label(slot, exp_phase), \
            (slot, exp_phase, got)

data = {
    "generated": "2026-10-15",
    "seed": sd.SEED,
    "snapshot": sd.SNAP.isoformat(),
    "baseSlots": len(sd.BASE_SLOTS),
    "slots": slots,
    "phases": phases,
    "seq": seq,
    "papers": papers,
}
out = ROOT / "scripts" / "intake_screen" / "draw_data.json"
out.parent.mkdir(exist_ok=True)
with open(out, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    f.write("\n")
print(f"export ok: {out} ({out.stat().st_size} bytes); "
      f"2000 equivalence trials passed; "
      f"slots {[ (s['name'], len(seq[s['name']])) for s in slots ]}")
