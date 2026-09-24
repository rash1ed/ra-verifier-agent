from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
from typing import Any


VALID_STATUSES = {"PASS", "FAIL", "HOLD"}


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    reasons: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
@dataclass
class Criteria:
    required_files: list[str] = field(default_factory=list)
    expected_sha256: dict[str, str] = field(default_factory=dict)
    test_command: list[str] | None = None
    test_timeout_seconds: int = 120
    secret_scan: bool = True
    claim_rules: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str | Path) -> "Criteria":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            required_files=[str(x) for x in payload.get("required_files", [])],
            expected_sha256={
                str(k): str(v).lower()
                for k, v in payload.get("expected_sha256", {}).items()
            },
            test_command=payload.get("test_command"),
            test_timeout_seconds=int(payload.get("test_timeout_seconds", 120)),
            secret_scan=bool(payload.get("secret_scan", True)),
            claim_rules=list(payload.get("claim_rules", [])),
        )
@dataclass
class VerifyResult:
    artifact: str
    status: str
    checks: list[CheckResult]

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": self.artifact,
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
        }
