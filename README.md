# RA Verifier Agent v0.1

Evidence-first verifier for project artifacts.

## What it verifies

- required files
- expected SHA-256 hashes
- a configured test command
- simple secret patterns
- numeric claim-to-evidence consistency

The verifier does **not** repair artifacts. Test commands run against a temporary copy so verification does not mutate the source artifact.

## Verified v0.1 status

- **8 / 8 verifier tests passing**
- Excel Assurance Engine verification: **PASS**
- Required files: PASS
- Test execution: PASS
- Secret scan: PASS
- Claim-to-evidence comparison: PASS
- SHA-256 support implemented; the current Excel criteria does not require fixed hashes
Public evidence:
- [Verifier test transcript](docs/validation.txt)
- [Excel Engine verification example](docs/excel-engine-verification.txt)
- [CI workflow](.github/workflows/ci.yml)

## Status model

- PASS: every configured check passed
- FAIL: at least one check produced a concrete failure
- HOLD: no concrete failure was found, but at least one check could not be completed

## Run

```bash
python -m verifier --artifact <artifact-directory> --criteria <criteria.json>
```

## Excel Assurance Engine example

```bash
python -m verifier \
  --artifact <path-to-excel-engine> \
  --criteria criteria/excel_engine.json \
  --json-report verifier-output/excel_engine.json \
  --text-report verifier-output/excel_engine.txt
```
## Design choices

- Python standard library at runtime
- pytest is used only for the verifier's development/test suite
- configured tests run against a temporary copy
- every check returns PASS, FAIL, or HOLD
- no automatic remediation

## v0.1 limitations

- local directory artifacts only
- regex-based secret scan, not a full secret-management product
- claim comparison requires explicit regex rules
- external URL/GitHub verification is outside v0.1
- no remediation is performed

## License

MIT
