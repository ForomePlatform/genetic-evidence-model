"""Tests for the annotation-worksheet converter (forome.gem.extraction.worksheet_to_yaml).

Every test fills a copy of the real template, templates/GEM_annotation_worksheet.xlsx,
so a drift between the template and the converter (Effort columns, pass codes,
worksheet version) fails here rather than in the study. Google Sheets exports a
typed 1 as the number 1.0 and date cells as midnight datetimes; several tests
reproduce exactly those exports.
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

import openpyxl  # the dev extra installs it: these tests must fail, never skip, without it
import yaml

from forome.gem.extraction import worksheet_to_yaml as W

TEMPLATE = Path(__file__).resolve().parents[6] / "templates" / "GEM_annotation_worksheet.xlsx"


def _col(ws, header):
    return [c.value for c in ws[1]].index(header) + 1


def _set_paper(wb, key, value):
    ws = wb["Paper"]
    for r in ws.iter_rows():
        if r[0].value == key:
            # .value, not cell(value=...): openpyxl's cell() ignores value=None
            ws.cell(row=r[0].row, column=2).value = value
            return
    raise KeyError(key)


def _filled(tmp_path, mutate=None, name="ws.xlsx"):
    """The template filled with one valid item and assertion; mutate(wb) adjusts it."""
    wb = openpyxl.load_workbook(TEMPLATE)
    for k, v in (("paper_id", "smith2024"), ("citation", "Smith J, J Genet, 2024;1:1"),
                 ("title", "A title"), ("annotator", "A. Annotator"),
                 ("annotation_started", datetime.datetime(2026, 9, 1)),
                 ("annotation_finished", datetime.datetime(2026, 9, 2)), ("pass_code", "H0")):
        _set_paper(wb, k, v)
    it = wb["Items"]
    for h, v in (("item_id", "GE-1"), ("label", "A label"), ("knowledge_domain_1", "HUMAN_GENETICS"),
                 ("method_1", "STATISTICAL_GENETICS"), ("target_type", "GENE"), ("target", "TP53"),
                 ("resolution", "GENE"), ("phenotype_scale", "MOLECULAR"), ("credibility", "HIGH")):
        it.cell(row=3, column=_col(it, h), value=v)
    a = wb["Assertions"]
    for h, v in (("item_id", "GE-1"), ("assertion_number", 1), ("statement", "S."),
                 ("page", 2), ("key_phrase", "a short verbatim phrase")):
        a.cell(row=3, column=_col(a, h), value=v)
    e = wb["Effort"]
    for h, v in (("date", datetime.datetime(2026, 9, 1)), ("activity", "reading"),
                 ("start_time", datetime.time(14, 30)), ("stop_time", datetime.time(15, 0)),
                 ("minutes", 30)):
        e.cell(row=3, column=_col(e, h), value=v)
    if mutate:
        mutate(wb)
    path = tmp_path / name
    wb.save(path)
    return path


def _run(monkeypatch, capsys, worksheet, output, *extra):
    monkeypatch.setattr(sys, "argv", ["gem-worksheet-to-yaml", str(worksheet), str(output), *extra])
    code = W.main()
    return code, capsys.readouterr().out


def _out(tmp_path, paper="smith2024", name="h0"):
    return tmp_path / "processed" / paper / name / f"{name}.yaml"


def _add_ce(wb, ce_id, ref):
    ce = wb["Candidate Extensions"]
    ce.cell(row=3, column=_col(ce, "ce_id"), value=ce_id)
    ce.cell(row=3, column=_col(ce, "dimension_or_area"), value="target")
    ce.cell(row=3, column=_col(ce, "description"), value="d")
    it = wb["Items"]
    it.cell(row=3, column=_col(it, "candidate_extension_refs"), value=ref)


# ---- the template and the converter agree ---------------------------------------------

def test_template_matches_converter():
    assert TEMPLATE.is_file(), TEMPLATE  # a moved template must fail loudly
    wb = openpyxl.load_workbook(TEMPLATE)
    paper = {r[0].value: r[1].value for r in wb["Paper"].iter_rows()}
    assert paper["worksheet_version"] in W.SUPPORTED_WORKSHEET_VERSIONS
    assert isinstance(paper["protocol_version"], str)  # text cell: "1.0" must not become 1
    assert [c.value for c in wb["Effort"][1]] == W.EFFORT_COLS
    en = wb["Enums"]
    j = [c.value for c in en[1]].index("PASS_CODE") + 1
    codes = [en.cell(row=i, column=j).value for i in range(2, en.max_row + 1)]
    assert [c for c in codes if c] == list(W.PASS_OUTPUT)


# ---- a valid worksheet ------------------------------------------------------------------

def test_valid_worksheet_converts(tmp_path, monkeypatch, capsys):
    out, eff = _out(tmp_path), tmp_path / "processed" / "smith2024" / "h0" / "effort.csv"
    code, log = _run(monkeypatch, capsys, _filled(tmp_path), out, "--effort", str(eff))
    assert code == 0, log
    doc = yaml.safe_load(out.read_text())
    prov = doc["provenance"]
    assert prov["pass_code"] == "H0" and prov["protocol_version"] == "1.1"
    assert prov["annotated_at"] == "2026-09-02" and prov["annotation_started"] == "2026-09-01"
    assert prov["conversion"]["worksheet_version"] == "2"
    assert "annotated_at_defaulted" not in prov["conversion"]
    raw = eff.read_bytes()
    assert b"\r" not in raw and b"\r" not in out.read_bytes()
    header, row = raw.decode().splitlines()[:2]
    assert header.split(",") == ["paper_id", "pass_code", "annotator"] + W.EFFORT_COLS
    assert row.startswith("smith2024,H0,A. Annotator,2026-09-01,reading,14:30,15:00,30,")


def test_blank_annotation_finished_defaults_and_is_marked(tmp_path, monkeypatch, capsys):
    ws = _filled(tmp_path, lambda wb: _set_paper(wb, "annotation_finished", None))
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path))
    assert code == 0 and "annotated_at defaults to the conversion date" in log
    prov = yaml.safe_load(_out(tmp_path).read_text())["provenance"]
    assert prov["annotated_at"] == datetime.date.today().isoformat()
    assert prov["conversion"]["annotated_at_defaulted"] is True


# ---- Google Sheets typing ---------------------------------------------------------------

def test_numeric_ce_id_matches_numeric_ref(tmp_path, monkeypatch, capsys):
    ws = _filled(tmp_path, lambda wb: _add_ce(wb, 1, 1))  # both exported as numbers
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path))
    assert code == 0, log
    assert "is not in the CE-<n> form" in log  # kept as typed, flagged
    doc = yaml.safe_load(_out(tmp_path).read_text())
    assert doc["candidate_extensions"][0]["id"] == "1"
    assert doc["evidence"][0]["candidate_extension_exercised"] == "1"


def test_refs_may_be_comma_separated(tmp_path, monkeypatch, capsys):
    def two(wb):
        _add_ce(wb, "CE-1", "CE-1, CE-2")
        ce = wb["Candidate Extensions"]
        ce.cell(row=4, column=_col(ce, "ce_id"), value="CE-2")
    code, log = _run(monkeypatch, capsys, _filled(tmp_path, two), _out(tmp_path))
    assert code == 0, log
    e = yaml.safe_load(_out(tmp_path).read_text())["evidence"][0]
    assert e["candidate_extension_exercised"] == "CE-1"
    assert e["candidate_extension_note"] == "Also exercises: CE-2"


def test_dangling_ref_is_an_error(tmp_path, monkeypatch, capsys):
    code, log = _run(monkeypatch, capsys, _filled(tmp_path, lambda wb: _add_ce(wb, 1, 2)),
                     _out(tmp_path))
    assert code == 1 and "candidate_extension_refs '2' not on" in log
    assert not _out(tmp_path).exists()


def test_duplicate_ce_id_is_an_error(tmp_path, monkeypatch, capsys):
    def dup(wb):
        _add_ce(wb, 1, 1)
        wb["Candidate Extensions"].cell(row=4, column=1, value="1")  # number vs text
    code, log = _run(monkeypatch, capsys, _filled(tmp_path, dup), _out(tmp_path))
    assert code == 1 and "duplicate ce_id" in log


def test_assertion_number_typed_as_text(tmp_path, monkeypatch, capsys):
    a_col = lambda wb: _col(wb["Assertions"], "assertion_number")  # noqa: E731
    ok = _filled(tmp_path, lambda wb: wb["Assertions"].cell(row=3, column=a_col(wb), value="1"))
    code, log = _run(monkeypatch, capsys, ok, _out(tmp_path))
    assert code == 0, log
    bad = _filled(tmp_path, lambda wb: wb["Assertions"].cell(row=3, column=a_col(wb), value="1a"),
                  name="bad.xlsx")
    code, log = _run(monkeypatch, capsys, bad, tmp_path / "bad.yaml")
    assert code == 1 and "is not a whole number" in log


def test_assertions_numbered_by_number_and_text_sort_together(tmp_path, monkeypatch, capsys):
    def two(wb):
        a = wb["Assertions"]
        for h, v in (("item_id", "GE-1"), ("assertion_number", "2"), ("statement", "T."),
                     ("page", 3), ("key_phrase", "another phrase")):
            a.cell(row=4, column=_col(a, h), value=v)
    code, log = _run(monkeypatch, capsys, _filled(tmp_path, two), _out(tmp_path))
    assert code == 0, log
    ids = [x["id"] for x in yaml.safe_load(_out(tmp_path).read_text())["evidence"][0]["assertions"]]
    assert ids == ["GE-1.A1", "GE-1.A2"]


# ---- worksheet version 2 and the study layout ------------------------------------------

def test_version_1_worksheet_is_rejected(tmp_path, monkeypatch, capsys):
    ws = _filled(tmp_path, lambda wb: _set_paper(wb, "worksheet_version", None))
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path))
    assert code == 1 and "predates version 2 and must be migrated" in log


def test_missing_effort_columns_are_an_error(tmp_path, monkeypatch, capsys):
    def drop(wb):
        wb["Effort"].cell(row=1, column=_col(wb["Effort"], "interruptions")).value = None
    code, log = _run(monkeypatch, capsys, _filled(tmp_path, drop), _out(tmp_path))
    assert code == 1 and "missing column(s) interruptions" in log


def test_pass_code_must_match_output_name(tmp_path, monkeypatch, capsys):
    ws = _filled(tmp_path, lambda wb: _set_paper(wb, "pass_code", "SR"))  # copied H0 sheet, code updated
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path, name="h0"))
    assert code == 1 and "pass_code SR produces h1.yaml" in log
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path, name="h1"))
    assert code == 0, log


def test_paper_directory_must_match_paper_id(tmp_path, monkeypatch, capsys):
    code, log = _run(monkeypatch, capsys, _filled(tmp_path), _out(tmp_path, paper="jones2023"))
    assert code == 1 and "does not match paper_id 'smith2024'" in log


def test_numeric_protocol_version_is_recorded_with_a_warning(tmp_path, monkeypatch, capsys):
    ws = _filled(tmp_path, lambda wb: _set_paper(wb, "protocol_version", 1.1))
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path))
    assert code == 0 and "protocol_version is stored as a number" in log
    assert yaml.safe_load(_out(tmp_path).read_text())["provenance"]["protocol_version"] == "1.1"


@pytest.mark.parametrize("value, message", [
    (None, "'pass_code' is empty"),
    ("sr", "pass_code 'sr' is not one of H0, SR, WR"),
])
def test_pass_code_must_be_a_protocol_code(tmp_path, monkeypatch, capsys, value, message):
    ws = _filled(tmp_path, lambda wb: _set_paper(wb, "pass_code", value))
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path))
    assert code == 1 and message in log


@pytest.mark.parametrize("value, message", [
    (None, "'protocol_version' is empty"),
    (1, "protocol_version 1 is not a version"),  # a typed 1.0 exported as an int
    (datetime.datetime(2026, 1, 1), "is not a version"),  # locale-parsed as a date
])
def test_protocol_version_must_be_a_version(tmp_path, monkeypatch, capsys, value, message):
    ws = _filled(tmp_path, lambda wb: _set_paper(wb, "protocol_version", value))
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path))
    assert code == 1 and message in log


def test_unsupported_worksheet_version_is_an_error(tmp_path, monkeypatch, capsys):
    ws = _filled(tmp_path, lambda wb: _set_paper(wb, "worksheet_version", "3"))
    code, log = _run(monkeypatch, capsys, ws, _out(tmp_path))
    assert code == 1 and "worksheet_version '3' is not supported" in log


def test_failed_run_leaves_earlier_outputs_untouched(tmp_path, monkeypatch, capsys):
    out, eff = _out(tmp_path), tmp_path / "processed" / "smith2024" / "h0" / "effort.csv"
    assert _run(monkeypatch, capsys, _filled(tmp_path), out, "--effort", str(eff))[0] == 0
    before = out.read_bytes(), eff.read_bytes()
    bad = _filled(tmp_path, lambda wb: _set_paper(wb, "title", None), name="bad.xlsx")
    assert _run(monkeypatch, capsys, bad, out, "--effort", str(eff))[0] == 1
    assert (out.read_bytes(), eff.read_bytes()) == before


def test_effort_dates_outside_the_pass_are_flagged(tmp_path, monkeypatch, capsys):
    def stale(wb):  # a sitting inherited from an earlier pass, and a mistyped year
        e = wb["Effort"]
        e.cell(row=4, column=_col(e, "date"), value=datetime.datetime(2026, 8, 1))
        e.cell(row=5, column=_col(e, "date"), value=datetime.datetime(2926, 10, 5))
    code, log = _run(monkeypatch, capsys, _filled(tmp_path, stale), _out(tmp_path))
    assert code == 0, log  # advisory only: the rows are kept as typed
    assert "2026-08-01 is before annotation_started 2026-09-01" in log
    assert "2926-10-05 is in the future" in log


def test_effort_date_with_a_time_of_day_does_not_crash(tmp_path, monkeypatch, capsys):
    def timed(wb):
        e = wb["Effort"]
        e.cell(row=3, column=_col(e, "date"), value=datetime.datetime(2026, 9, 1, 14, 30))
    code, log = _run(monkeypatch, capsys, _filled(tmp_path, timed), _out(tmp_path))
    assert code == 0, log
