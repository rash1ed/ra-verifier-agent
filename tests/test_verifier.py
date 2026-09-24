from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys
import tempfile

import pytest

from verifier.models import Criteria
from verifier.verifier import verify


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def base_project(root: Path) -> Path:
    write(root / "README.md", "Project claims 3 tests passing.\n")
    write(root / "docs" / "validation.txt", "Ran 3 tests\nOK\n")
    write(root / "data.txt", "safe data\n")
    return root


def criteria(**overrides) -> Criteria:
    payload = dict(
        required_files=["README.md", "docs/validation.txt"],
        expected_sha256={},
        test_command=None,
        test_timeout_seconds=30,
        secret_scan=True,
        claim_rules=[{
            "claim_file": "README.md",
            "claim_regex": r"(\d+) tests passing",
            "evidence_file": "docs/validation.txt",
            "evidence_regex": r"Ran (\d+) tests",
        }],
    )
    payload.update(overrides)
    return Criteria(**payload)
def test_tests_pass():
    with tempfile.TemporaryDirectory() as tmp:
        root = base_project(Path(tmp))
        write(root / "test_demo.py", "def test_ok():\n    assert 2 + 2 == 4\n")
        result = verify(
            root,
            criteria(test_command=[sys.executable, "-m", "pytest", "-q"]),
        )
        assert result.status == "PASS"
        test_check = next(c for c in result.checks if c.name == "tests")
        assert test_check.status == "PASS"


def test_tests_fail():
    with tempfile.TemporaryDirectory() as tmp:
        root = base_project(Path(tmp))
        write(root / "test_demo.py", "def test_bad():\n    assert False\n")
        result = verify(
            root,
            criteria(test_command=[sys.executable, "-m", "pytest", "-q"]),
        )
        assert result.status == "FAIL"
        test_check = next(c for c in result.checks if c.name == "tests")
        assert test_check.status == "FAIL"


def test_missing_required_file():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root / "README.md", "Project claims 3 tests passing.\n")
        result = verify(root, criteria())
        assert result.status == "FAIL"
        check = next(c for c in result.checks if c.name == "required_files")
        assert "docs/validation.txt" in " ".join(check.reasons)
def test_sha256_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        root = base_project(Path(tmp))
        result = verify(
            root,
            criteria(expected_sha256={"data.txt": "0" * 64}),
        )
        assert result.status == "FAIL"
        check = next(c for c in result.checks if c.name == "sha256")
        assert check.status == "FAIL"


def test_secret_detected():
    with tempfile.TemporaryDirectory() as tmp:
        root = base_project(Path(tmp))
        write(root / "config.txt", 'api_key = "sk-test-123456789012345"\n')
        result = verify(root, criteria())
        assert result.status == "FAIL"
        check = next(c for c in result.checks if c.name == "secret_scan")
        assert check.status == "FAIL"


def test_claim_mismatch():
    with tempfile.TemporaryDirectory() as tmp:
        root = base_project(Path(tmp))
        write(root / "README.md", "Project claims 5 tests passing.\n")
        result = verify(root, criteria())
        assert result.status == "FAIL"
        check = next(c for c in result.checks if c.name == "claim_evidence")
        assert "5 != 3" in " ".join(check.reasons)


def test_clean_project_passes():
    with tempfile.TemporaryDirectory() as tmp:
        root = base_project(Path(tmp))
        digest = hashlib.sha256((root / "data.txt").read_bytes()).hexdigest()
        result = verify(
            root,
            criteria(expected_sha256={"data.txt": digest}),
        )
        assert result.status == "PASS"
def test_verifier_does_not_mutate_artifact_when_running_tests():
    with tempfile.TemporaryDirectory() as tmp:
        root = base_project(Path(tmp))
        write(
            root / "mutating_test.py",
            "from pathlib import Path\n"
            "Path('generated.txt').write_text('temp', encoding='utf-8')\n"
            "print('1 passed')\n",
        )
        before = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        result = verify(
            root,
            criteria(test_command=[sys.executable, "mutating_test.py"]),
        )
        after = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
        assert result.status == "PASS"
        assert before == after
        assert not (root / "generated.txt").exists()
