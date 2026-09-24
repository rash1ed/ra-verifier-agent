from __future__ import annotations

from pathlib import Path

from .checks import (
    check_claim_rules,
    check_hashes,
    check_required_files,
    check_secrets,
    run_tests,
)
from .models import CheckResult, Criteria, VerifyResult


def _overall(checks: list[CheckResult]) -> str:
    if any(check.status == "FAIL" for check in checks):
        return "FAIL"
    if any(check.status == "HOLD" for check in checks):
        return "HOLD"
    return "PASS"


def verify(artifact: str | Path, criteria: Criteria) -> VerifyResult:
    root = Path(artifact).resolve()
    if not root.exists():
        check = CheckResult(
            "artifact", "FAIL", [f"Artifact not found: {root}"], [str(root)]
        )
        return VerifyResult(str(root), "FAIL", [check])
    if not root.is_dir():
        check = CheckResult(
            "artifact", "HOLD",
            ["v0.1 currently verifies directory artifacts."],
            [str(root)],
        )
        return VerifyResult(str(root), "HOLD", [check])

    checks: list[CheckResult] = [
        check_required_files(root, criteria.required_files),
        check_hashes(root, criteria.expected_sha256),
        run_tests(root, criteria.test_command, criteria.test_timeout_seconds),
    ]
    if criteria.secret_scan:
        checks.append(check_secrets(root))
    else:
        checks.append(
            CheckResult(
                "secret_scan", "PASS",
                ["Secret scan disabled by criteria."], [],
            )
        )

    checks.append(check_claim_rules(root, criteria.claim_rules))
    return VerifyResult(str(root), _overall(checks), checks)
