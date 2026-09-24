from __future__ import annotations

from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import tempfile

from .models import CheckResult


TEXT_EXTS = {
    ".py", ".md", ".txt", ".json", ".toml", ".yml", ".yaml",
    ".ini", ".cfg", ".html", ".css", ".js", ".ts", ".xml", ".csv",
}

SECRET_PATTERNS = {
    "openai_token": re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_pat": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "assigned_secret": re.compile(
        r"""(?ix)\b(password|api[_-]?key|secret|token)\b\s*[:=]\s*
        ["']?([A-Za-z0-9_./+=-]{10,})["']?"""
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
def check_required_files(artifact: Path, required: list[str]) -> CheckResult:
    missing = [rel for rel in required if not (artifact / rel).exists()]
    if missing:
        return CheckResult(
            name="required_files",
            status="FAIL",
            reasons=[f"Missing required file: {rel}" for rel in missing],
            evidence_refs=missing,
        )
    return CheckResult(
        name="required_files",
        status="PASS",
        reasons=[f"{len(required)} required file(s) present."],
        evidence_refs=required,
    )


def check_hashes(artifact: Path, expected: dict[str, str]) -> CheckResult:
    reasons: list[str] = []
    refs: list[str] = []
    for rel, want in expected.items():
        path = artifact / rel
        if not path.exists():
            reasons.append(f"Cannot hash missing file: {rel}")
            continue
        got = _sha256(path)
        refs.append(rel)
        if got.lower() != want.lower():
            reasons.append(f"SHA256 mismatch for {rel}: expected {want}, got {got}")
    if reasons:
        return CheckResult("sha256", "FAIL", reasons, refs)
    return CheckResult(
        "sha256", "PASS",
        [f"{len(expected)} SHA256 expectation(s) matched."],
        refs,
    )
def run_tests(artifact: Path, command: list[str] | None, timeout: int) -> CheckResult:
    if not command:
        return CheckResult(
            "tests", "PASS", ["No test command required by criteria."], []
        )
    with tempfile.TemporaryDirectory(prefix="ra_verifier_") as tmp:
        work = Path(tmp) / "artifact"
        shutil.copytree(
            artifact, work,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )
        try:
            proc = subprocess.run(
                command,
                cwd=work,
                text=True,
                capture_output=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            return CheckResult(
                "tests", "HOLD",
                [f"Test command timed out after {timeout}s."],
                [" ".join(command)],
            )
        except OSError as exc:
            return CheckResult(
                "tests", "HOLD",
                [f"Test command could not start: {exc}"],
                [" ".join(command)],
            )
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()
        tail = "\n".join(output.splitlines()[-30:])
        status = "PASS" if proc.returncode == 0 else "FAIL"
        return CheckResult(
            "tests", status,
            [f"Exit code: {proc.returncode}"],
            [" ".join(command)],
            {"output_tail": tail},
        )
def check_secrets(artifact: Path) -> CheckResult:
    hits: list[str] = []
    for path in artifact.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_EXTS and path.name != ".env":
            continue
        if path.stat().st_size > 2_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = str(path.relative_to(artifact))
        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                snippet = match.group(0)
                # Do not treat regex examples/pattern declarations as secrets.
                line = text[max(0, match.start()-80):match.end()+80]
                if "re.compile" in line or "SECRET_PATTERNS" in line:
                    continue
                hits.append(f"{rel}: {label}: {snippet[:12]}...")
    if hits:
        return CheckResult(
            "secret_scan", "FAIL",
            [f"Potential secret pattern found: {hit}" for hit in hits],
            hits,
        )
    return CheckResult(
        "secret_scan", "PASS", ["No secret patterns found."], []
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")
def check_claim_rules(artifact: Path, rules: list[dict]) -> CheckResult:
    reasons: list[str] = []
    refs: list[str] = []
    for index, rule in enumerate(rules, start=1):
        claim_file = artifact / str(rule.get("claim_file", "README.md"))
        evidence_file = artifact / str(rule.get("evidence_file", ""))
        claim_re = str(rule.get("claim_regex", ""))
        evidence_re = str(rule.get("evidence_regex", ""))
        if not claim_file.exists():
            reasons.append(f"Rule {index}: claim file missing: {claim_file.relative_to(artifact)}")
            continue
        if not evidence_file.exists():
            reasons.append(f"Rule {index}: evidence file missing: {evidence_file.relative_to(artifact)}")
            continue
        refs.extend([
            str(claim_file.relative_to(artifact)),
            str(evidence_file.relative_to(artifact)),
        ])
        try:
            claim_match = re.search(claim_re, _read_text(claim_file), re.I | re.M)
            evidence_match = re.search(evidence_re, _read_text(evidence_file), re.I | re.M)
        except re.error as exc:
            return CheckResult(
                "claim_evidence", "HOLD",
                [f"Rule {index}: invalid regex: {exc}"], refs,
            )
        if not claim_match:
            reasons.append(f"Rule {index}: claim pattern not found.")
            continue
        if not evidence_match:
            reasons.append(f"Rule {index}: evidence pattern not found.")
            continue
        claim_value = claim_match.group(1) if claim_match.groups() else claim_match.group(0)
        evidence_value = evidence_match.group(1) if evidence_match.groups() else evidence_match.group(0)
        if claim_value != evidence_value:
            reasons.append(
                f"Rule {index}: claim-evidence mismatch: {claim_value} != {evidence_value}"
            )
    if reasons:
        return CheckResult("claim_evidence", "FAIL", reasons, refs)
    return CheckResult(
        "claim_evidence", "PASS",
        [f"{len(rules)} claim rule(s) matched evidence."],
        refs,
    )
