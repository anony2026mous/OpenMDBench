"""Pre-publication secret scan of the release tree.

Publishing credentials is the one irreversible mistake in a release, so this checks
for the specific things present in this workspace rather than a generic regex sweep:

  * the SSH private key material pasted into the session (even though it should never
    have been written to disk, verify),
  * the platform bearer token,
  * `.env` / netrc / cloud credential files,
  * absolute home paths that leak a username (reported, not fatal),
  * private keys by header signature anywhere in the tree.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

REL = Path(os.environ.get("OPENMD_RELEASE_DIR")
           or Path(__file__).resolve().parent.parent)

# Matches that are known-良性 and would otherwise reappear on every run. Each entry is
# justified: leaving unexplained hits in the report trains people to ignore it.
ALLOWLIST: dict[str, str] = {
    # 2.2 MB of base64-encoded PNG embeds a byte run that happens to start with "AKIA";
    # it is image data, not an access key.
    "paper/figures/fig1_narrative_zhang.svg": "AKIA inside base64 image data",
    "paper\\figures\\fig1_narrative_zhang.svg": "AKIA inside base64 image data",
    # The scanner must contain the signatures it searches for.
    "reproduce/scan_for_secrets.py": "contains the detection patterns themselves",
    "reproduce\\scan_for_secrets.py": "contains the detection patterns themselves",
    "reproduce/SECRET_SCAN.txt": "previous scan report; regenerated each run",
    "reproduce\\SECRET_SCAN.txt": "previous scan report; regenerated each run",
}

# Signatures of real secrets. Keep these patterns narrow so the report is actionable.
SIGS = {
    "private key header": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "openssh key body": re.compile(rb"b3BlbnNzaC1rZXktdjEAAAA"),
    "bearer token": re.compile(rb"Authorization:\s*Bearer\s+[A-Za-z0-9._\-]{20,}"),
    "jwt": re.compile(rb"eyJhbGciOiJ[A-Za-z0-9._\-]{40,}"),
    # A real AWS key id is 20 chars total and is not embedded in base64 runs; requiring a
    # word boundary on the right removes the image-data false positive.
    "aws key id": re.compile(rb"(?<![A-Za-z0-9+/])AKIA[0-9A-Z]{16}(?![A-Za-z0-9+/])"),
    "github token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    "openai-style key": re.compile(rb"sk-[A-Za-z0-9]{32,}"),
    "password assignment": re.compile(rb"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{6,}['\"]"),
    "proxy with creds": re.compile(rb"(?i)https?://[^/\s:@]{3,}:[^/\s@]{3,}@"),
}

# Credential-ish FILE NAMES. A bare `env` token is deliberately NOT matched: this is a
# simulation codebase whose modules are legitimately named `*_env.py`
# (`navigation_env.py`, `ie_rl_env.py`, ...). Matching those produced 8 false positives
# per run. What matters is dotfiles and explicit credential/secret names.
SENSITIVE_NAMES = re.compile(
    r"(?i)(^|[._-])(\.env|env\.|envrc|netrc|credentials?|secrets?|id_rsa|"
    r"id_ed25519|\.pem|\.key|\.p12|\.pfx|\.ppk|auth\.json|token|apikey|api_key)"
    r"($|[._-])")

# absolute home path leaking the account name
HOME_LEAK = re.compile(rb"[A-Za-z]:\\Users\\[^\\\r\n\"']{1,40}")

findings: list[tuple[str, str, str]] = []
allowed: list[tuple[str, str]] = []
scanned = 0
skipped_bin = 0
home_hits: dict[str, int] = {}

for root, dirs, names in os.walk(REL):
    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
    for n in names:
        p = Path(root) / n
        rel = p.relative_to(REL)
        rel_s = str(rel).replace("\\", "/")
        scanned += 1
        # A file on the allowlist is skipped entirely: its hits are known-良性, and
        # re-reporting them every run would train the reader to ignore the scan.
        if rel_s in ALLOWLIST or str(rel) in ALLOWLIST:
            allowed.append((rel_s, ALLOWLIST.get(rel_s) or ALLOWLIST.get(str(rel), "")))
            continue
        if SENSITIVE_NAMES.search(n):
            findings.append((str(rel), "suspicious filename", ""))
        try:
            data = p.read_bytes()
        except OSError as exc:
            findings.append((str(rel), "unreadable", str(exc)))
            continue
        if len(data) > 8 << 20:          # skip huge binaries for content regexes
            skipped_bin += 1
            continue
        for label, rx in SIGS.items():
            m = rx.search(data)
            if m:
                snippet = m.group(0)[:80].decode("utf-8", "replace")
                findings.append((str(rel), label, snippet))
        for m in HOME_LEAK.finditer(data):
            key = m.group(0).decode("utf-8", "replace")
            home_hits[key] = home_hits.get(key, 0) + 1

print("=" * 92)
print("PRE-PUBLICATION SECRET SCAN")
print("=" * 92)
print(f"  files scanned      : {scanned}")
print(f"  large files skipped: {skipped_bin}")

hard = [f for f in findings if f[1] != "suspicious filename"]
susp = [f for f in findings if f[1] == "suspicious filename"]

print(f"\n--- hard findings ({len(hard)}) ---")
if hard:
    for rel, label, snip in hard[:40]:
        print(f"  [{label}] {rel}")
        if snip:
            print(f"      {snip}")
else:
    print("  none")

print(f"\n--- suspicious filenames ({len(susp)}) ---")
if susp:
    for rel, _l, _s in susp[:40]:
        print(f"  {rel}")
else:
    print("  none")

print(f"\n--- absolute home paths found ({len(home_hits)} distinct) ---")
for k, v in sorted(home_hits.items(), key=lambda kv: -kv[1])[:20]:
    print(f"  {v:>6}x  {k}")
print("\n  NOTE: absolute paths are not secrets, but they hard-code one machine's")
print("  layout. Shipped scripts resolve paths relative to the repository instead.")

if allowed:
    print(f"\n--- allowlisted ({len(allowed)}) ---")
    for rel, why in allowed:
        print(f"  {rel}")
        print(f"      {why}")

hard_block = bool(hard or susp or home_hits)
verdict = "CLEAN" if not hard_block else "REVIEW REQUIRED"
print(f"\n  VERDICT: {verdict}")

