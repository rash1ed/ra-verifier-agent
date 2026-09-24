from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys

from .models import Criteria
from .verifier import verify


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="ra-verify")
    parser.add_argument("--artifact", required=True, help="Artifact directory")
    parser.add_argument("--criteria", required=True, help="Criteria JSON path")
    parser.add_argument("--json-report", help="Write JSON report to this path")
    parser.add_argument("--text-report", help="Write text report to this path")
    return parser


def _text_report(result) -> str:
    lines = [f"RA Verifier Agent v0.1", f"Artifact: {result.artifact}", f"Status: {result.status}", ""]
    for check in result.checks:
        lines.append(f"[{check.status}] {check.name}")
        for reason in check.reasons:
            lines.append(f"  - {reason}")
        if check.evidence_refs:
            lines.append("  Evidence: " + ", ".join(check.evidence_refs))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    criteria = Criteria.from_json(args.criteria)
    result = verify(args.artifact, criteria)

    payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
    text_report = _text_report(result)

    print(text_report, end="")
    if args.json_report:
        path = Path(args.json_report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    if args.text_report:
        path = Path(args.text_report)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text_report, encoding="utf-8")

    return 0 if result.status == "PASS" else (1 if result.status == "FAIL" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
