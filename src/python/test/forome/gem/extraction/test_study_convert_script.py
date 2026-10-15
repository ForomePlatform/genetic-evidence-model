"""Tests for scripts/study-convert.sh, the study-layout converter wrapper.

The script is copied into a temporary repository skeleton, and a fake
gem-worksheet-to-yaml on PATH records how it was invoked, so the tests check
path construction and argument policing without needing openpyxl or a real
worksheet.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[6] / "scripts" / "study-convert.sh"
pytestmark = pytest.mark.skipif(os.name != "posix", reason="bash script")

FAKE_OK = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$FAKE_LOG"
pwd >> "$FAKE_LOG"
exit "${FAKE_EXIT:-0}"
"""


@pytest.fixture()
def repo(tmp_path):
    """A repository skeleton holding a copy of the script and a fake converter."""
    assert SCRIPT.is_file(), SCRIPT
    (tmp_path / "scripts").mkdir()
    script = tmp_path / "scripts" / "study-convert.sh"
    shutil.copy(SCRIPT, script)
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "gem-worksheet-to-yaml"
    fake.write_text(FAKE_OK)
    fake.chmod(0o755)
    raw = tmp_path / "study" / "raw" / "smith2024"
    raw.mkdir(parents=True)
    (raw / "h0.xlsx").write_bytes(b"not a real workbook")
    return tmp_path


def run(repo, *args, cwd=None, fake_exit=None, drop_fake=False):
    env = dict(os.environ)
    path = f"{repo / 'bin'}:{env['PATH']}"
    if drop_fake:
        path = env["PATH"]
    env.update(PATH=path, FAKE_LOG=str(repo / "fake.log"))
    if fake_exit is not None:
        env["FAKE_EXIT"] = str(fake_exit)
    return subprocess.run(
        ["bash", str(repo / "scripts" / "study-convert.sh"), *args],
        cwd=cwd or repo, env=env, capture_output=True, text=True)


def test_expands_the_study_layout(repo):
    r = run(repo, "smith2024", "h0")
    assert r.returncode == 0, r.stderr
    got = (repo / "fake.log").read_text().splitlines()
    assert got == [
        "study/raw/smith2024/h0.xlsx",
        "study/processed/smith2024/h0/h0.yaml",
        "--effort",
        "study/processed/smith2024/h0/effort.csv",
        str(repo),  # ran from the repository root
    ]
    assert "Next: gem-validate study/processed/smith2024/h0/h0.yaml" in r.stdout


def test_runs_from_any_directory(repo, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    r = run(repo, "smith2024", "h0", cwd=elsewhere)
    assert r.returncode == 0, r.stderr
    assert (repo / "fake.log").read_text().splitlines()[-1] == str(repo)


@pytest.mark.parametrize("args", [(), ("smith2024",), ("smith2024", "h0", "--force")])
def test_wrong_argument_count_is_usage_error(repo, args):
    r = run(repo, *args)
    assert r.returncode == 2 and "usage:" in r.stderr
    assert not (repo / "fake.log").exists()


def test_bad_pass_and_bad_paper_id_are_rejected(repo):
    r = run(repo, "smith2024", "sr")
    assert r.returncode == 2 and "not one of: h0 h1 h0r" in r.stderr
    r = run(repo, "Smith 2024", "h0")
    assert r.returncode == 2 and "not lowercase" in r.stderr
    assert not (repo / "fake.log").exists()


def test_missing_export_names_the_expected_path(repo):
    r = run(repo, "smith2024", "h1")
    assert r.returncode == 2
    assert "study/raw/smith2024/h1.xlsx" in r.stderr and "step 2" in r.stderr


def test_converter_failure_propagates_without_the_next_hint(repo):
    r = run(repo, "smith2024", "h0", fake_exit=3)
    assert r.returncode == 3
    assert "Next: gem-validate" not in r.stdout


def test_falls_back_to_the_module_file(repo):
    mod = repo / "src" / "python" / "main" / "forome" / "gem" / "extraction"
    mod.mkdir(parents=True)
    (mod / "worksheet_to_yaml.py").write_text(
        "import sys, pathlib\n"
        "pathlib.Path('fallback.log').write_text('\\n'.join(sys.argv[1:]))\n")
    r = run(repo, "smith2024", "h0", drop_fake=True)
    assert r.returncode == 0, r.stderr
    assert (repo / "fallback.log").read_text().splitlines()[0] == "study/raw/smith2024/h0.xlsx"
