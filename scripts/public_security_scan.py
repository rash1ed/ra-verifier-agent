from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {'.git', '.pytest_cache', '__pycache__', 'verifier-output'}
TEXT_EXTS = {'.py', '.md', '.txt', '.json', '.toml', '.yml', '.yaml'}
PATTERNS = {
    'local_user_path': re.compile(r'C:\\\\Users\\\\lllSl', re.I),
    'personal_email': re.compile(r'rashidalbloushi5@gmail\\.com', re.I),
    'github_pat': re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'),
}

findings = []
for path in ROOT.rglob('*'):
    if not path.is_file():
        continue
    if any(part in EXCLUDE_DIRS for part in path.parts):
        continue
    if path.suffix.lower() not in TEXT_EXTS and path.name not in {'.gitignore', 'LICENSE'}:
        continue
    text = path.read_text(encoding='utf-8', errors='ignore')
    for label, pattern in PATTERNS.items():
        if pattern.search(text):
            findings.append((str(path.relative_to(ROOT)), label))

print('PUBLIC_SCAN_FINDINGS', findings)
raise SystemExit(1 if findings else 0)
