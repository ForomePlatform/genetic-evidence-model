# Seal ledger

Append-only record of sealed study stages
(`protocols/EVALUATION_PROTOCOL.md` section 9). Each entry names the seal
commit and its annotated tag, which carries the same record. The ledger
entry is committed separately, immediately after the seal commit, because
a commit cannot contain the hashes of its own content.

Verify any listed file with: `git cat-file blob <blob-id> | shasum -a 256`.

## S-1: marques2025 H0 (manual annotation, first pass)

- Sealed: 2026-10-15 00:12:23 EDT by the study lead.
- Seal commit: 5cfd9d852d6a58303870cec62c951a03edf5f57f
- Tag: `study-marques2025-h0` (annotated)
- Paper: Marques et al. 2025, J. Psychiatry Neurosci. 50:E323-E333
  (doi:10.1139/jpn-25-0017); approved stress-stratum paper.
- Converter: worksheet_to_yaml v2.0, 0 errors, 2 advisory warnings.
- Validation: gem-validate PASS (all annotations conform to the SHACL
  shapes), 2026-10-15.
- Files (git blob id; sha256 of blob content):
  - `study/processed/marques2025/h0/effort.csv`
    blob `2c14fcce823cf8913810ed821880386b32c5db93`
    sha256 `8ea81ffd3c548b4f77094cd96c762c2fbd63a65dc1f18752b0834577f4b9aa21`
  - `study/processed/marques2025/h0/h0.yaml`
    blob `613b1011cab4bf3af5c0c51159cc90226dcb5952`
    sha256 `6c572b69155cd025f8b03c1192a07030be2864bdfec671a7cef7d851a64f6c52`
  - `study/raw/marques2025/h0.xlsx`
    blob `53d8d5523655d58c8aa0e900fa6ff62a7445e384`
    sha256 `59ac813fd1903dde66c5e8345e57ab58578ce6c7e91878d99b6c70a4e1472f56`
- Note: worksheet-version-2 metadata (pass_code, protocol_version,
  worksheet_version, five Effort columns) was applied by the study lead
  to the export locally; the source Google Sheet remains version 1 and
  carries identical annotation content, verified cell by cell against
  the live sheet on 2026-10-15.
