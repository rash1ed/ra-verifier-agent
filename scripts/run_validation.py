from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / 'docs' / 'validation.txt'

def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, encoding='utf-8', errors='replace')
    output = (proc.stdout or '') + (proc.stderr or '')
    return proc.returncode, output

def main() -> int:
    code, output = run([sys.executable, '-m', 'pytest', '-q'])
    text = '=== VERIFIER TESTS ===\n' + output.rstrip() + f'\nEXIT_CODE={code}\n'
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(text, encoding='utf-8')
    print(text, end='')
    return code

if __name__ == '__main__':
    raise SystemExit(main())
