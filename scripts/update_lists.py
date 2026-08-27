#!/usr/bin/env python3
"""
EDL Test Suite - EDL Manager
Unified script for creating and updating EDL list files in GitHub.

Subcommands
-----------
  init    Generate all 20 EDL list files locally and push them to GitHub.
          Run this once before starting the update loop.

  update  Randomly select a few EDL objects per type and update them.
          Repeats on --interval if given; otherwise runs once.

Usage examples
--------------
  # First-time setup: create all 20 EDL objects
  python update_lists.py init

  # Preview what init would push (no GitHub writes)
  python update_lists.py init --dry-run

  # Update a random subset every 1 minute
  python update_lists.py update --interval 1m

  # Update a random subset every 1 hour
  python update_lists.py update --interval 1h

  # One-shot random update
  python update_lists.py update

  # Preview which EDL objects would be selected (no GitHub writes)
  python update_lists.py update --dry-run

  # Override add/delete counts for this run
  python update_lists.py update --interval 1m --add 1000 --delete 300
"""
import argparse
import base64
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# Reuse generators and writer from generate_lists.py
sys.path.insert(0, str(Path(__file__).parent))
from generate_lists import (
    # IP generators
    gen_ip_01, gen_ip_02, gen_ip_03, gen_ip_04, gen_ip_05,
    # URL generators
    gen_url_01, gen_url_02, gen_url_03, gen_url_04, gen_url_05,
    # Domain generator (handles wildcards, IDN, edge via kwargs)
    gen_domains,
    # File writer
    _write,
    # Entry-level generators for incremental updates
    PUBLIC_IPV4_RANGES, PRIVATE_IPV4_RANGES,
    rand_ipv4, rand_ipv6, rand_domain,
    rand_url, rand_wildcard_domain, rand_idn_domain,
)

CONFIG_PATH = Path(__file__).parent / "config.yaml"
LISTS_DIR   = Path(__file__).parent / "lists"
GITHUB_API  = "https://api.github.com"

# Map each repo path suffix to its local generator and header
INIT_MANIFEST = [
    # (repo_subdir, filename,             local_gen_fn,  gen_kwargs,                           header)
    ("ip_lists",    "ip_list_01.txt", gen_ip_01, {},    "Public IPv4 (ARIN/RIPE/APNIC/LACNIC/AFRINIC cloud+ISP ranges)"),
    ("ip_lists",    "ip_list_02.txt", gen_ip_02, {},    "Private/Enterprise IPv4 + CGNAT"),
    ("ip_lists",    "ip_list_03.txt", gen_ip_03, {},    "IPv6 — real RIR allocations, ~8% CIDRs"),
    ("ip_lists",    "ip_list_04.txt", gen_ip_04, {},    "Mixed IPv4+IPv6, ~5% CIDRs — mixed-type stress test"),
    ("ip_lists",    "ip_list_05.txt", gen_ip_05, {},    "Edge cases: dups, IPv4-mapped IPv6, 6to4, Teredo, broadcast"),
    ("url_lists",   "url_list_01.txt", gen_url_01, {}, "Clean HTTPS URLs — diverse domains and paths"),
    ("url_lists",   "url_list_02.txt", gen_url_02, {}, "URLs with query parameters — analytics/tracking simulation"),
    ("url_lists",   "url_list_03.txt", gen_url_03, {}, "Wildcard URL patterns (*.domain.tld/path)"),
    ("url_lists",   "url_list_04.txt", gen_url_04, {}, "Custom port URLs — 8080/8443/9090/etc."),
    ("url_lists",   "url_list_05.txt", gen_url_05, {}, "Encoding edge cases: percent-enc, IDN, long paths, special chars"),
    ("domain_lists","domain_list_01.txt", gen_domains, {}, "Clean domains — .com/.net/.org weighted"),
    ("domain_lists","domain_list_02.txt", gen_domains, {}, "Clean domains — APNIC Asia-Pacific ccTLDs weighted"),
    ("domain_lists","domain_list_03.txt", gen_domains, {}, "Clean domains — RIPE European ccTLDs weighted"),
    ("domain_lists","domain_list_04.txt", gen_domains, {}, "Clean domains — mixed gTLDs (.app/.dev/.tech/.cloud)"),
    ("domain_lists","domain_list_05.txt", gen_domains, {}, "Clean domains — enterprise/cloud subdomains"),
    ("domain_lists","domain_list_06.txt", gen_domains, {}, "Clean domains — tech/startup themed"),
    ("domain_lists","domain_list_07.txt", gen_domains, {}, "Clean domains — LACNIC/AFRINIC ccTLDs weighted"),
    ("domain_lists","domain_list_08.txt", gen_domains, {}, "Clean domains — .gov/.edu/.mil/.int"),
    ("domain_lists","domain_list_09.txt", gen_domains, {"wildcards": True}, "Wildcard domains (*.domain.tld) — 20% wildcard ratio"),
    ("domain_lists","domain_list_10.txt", gen_domains, {"idn": True, "edge": True}, "IDN (Punycode) + deep subdomain edge cases"),
]


# ---------------------------------------------------------------------------
# GitHub API client
# ---------------------------------------------------------------------------

class GitHubClient:
    def __init__(self, token: str, repo: str, branch: str = "main",
                 ca_bundle: str | None = None):
        self.repo   = repo
        self.branch = branch
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if ca_bundle:
            self.session.verify = ca_bundle

    def _url(self, path: str) -> str:
        return f"{GITHUB_API}/repos/{self.repo}/contents/{path.lstrip('/')}"

    def get_file(self, path: str) -> tuple[str, str] | None:
        """Returns (decoded_content, sha) or None if file not found."""
        r = self.session.get(self._url(path), params={"ref": self.branch})
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        decoded = base64.b64decode(
            data.get("content", "").replace("\n", "")
        ).decode("utf-8")
        return decoded, data["sha"]

    def put_file(self, path: str, content: str, sha: str | None,
                 message: str) -> dict:
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": self.branch,
        }
        if sha:
            payload["sha"] = sha
        r = self.session.put(self._url(path), json=payload)
        r.raise_for_status()
        return r.json()

    def rate_limit(self) -> dict:
        r = self.session.get(f"{GITHUB_API}/rate_limit")
        r.raise_for_status()
        return r.json()["resources"]["core"]


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(path: str = str(CONFIG_PATH)) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

def resolve_ca(config: dict, config_path: str) -> str | None:
    ca = config["github"].get("ca_bundle")
    if ca and not Path(ca).is_absolute():
        ca = str(Path(config_path).parent / ca)
    return ca

def make_client(config: dict, config_path: str) -> GitHubClient:
    # GH_TOKEN env var takes precedence (used in GitHub Actions)
    token = os.environ.get("GH_TOKEN") or config["github"]["token"]
    # GITHUB_REPOSITORY is auto-set by GitHub Actions to "owner/repo" of the
    # current repo — this makes the script work in any fork without config changes
    repo = os.environ.get("GITHUB_REPOSITORY") or config["github"]["repo"]
    ca = resolve_ca(config, config_path)
    if ca and not Path(ca).exists():
        ca = None   # skip if file absent (e.g. running on GitHub Actions)
    return GitHubClient(
        token=token,
        repo=repo,
        branch=config["github"].get("branch", "main"),
        ca_bundle=ca,
    )


# ---------------------------------------------------------------------------
# Incremental entry generators (used by `update` subcommand)
# ---------------------------------------------------------------------------

def new_ip_entries(n: int) -> list[str]:
    out = []
    for _ in range(n):
        if random.random() < 0.30:
            out.append(rand_ipv6())
        else:
            s, e = random.choice(PUBLIC_IPV4_RANGES + PRIVATE_IPV4_RANGES)
            out.append(rand_ipv4(s, e))
    return out

def new_url_entries(n: int) -> list[str]:
    out = []
    for _ in range(n):
        r = random.random()
        if r < 0.15:
            out.append(rand_url(wildcards=True))
        elif r < 0.25:
            out.append(rand_url(custom_port=True))
        else:
            out.append(rand_url())
    return out

def new_domain_entries(n: int) -> list[str]:
    out = []
    for _ in range(n):
        r = random.random()
        if r < 0.15:
            out.append(rand_wildcard_domain())
        elif r < 0.22:
            out.append(rand_idn_domain())
        else:
            out.append(rand_domain())
    return out

ENTRY_GENERATORS = {"ip": new_ip_entries, "url": new_url_entries, "domain": new_domain_entries}

def infer_type(path: str) -> str:
    p = path.lower()
    if "ip_" in p or "/ip/" in p:
        return "ip"
    if "url_" in p or "/url/" in p:
        return "url"
    return "domain"


# ---------------------------------------------------------------------------
# File list builder
# ---------------------------------------------------------------------------

def build_file_list(config: dict, types: list[str]) -> list[str]:
    """Return all configured files for the given types."""
    files = []
    for t in types:
        files.extend(config.get("lists", {}).get(t, []))
    return files


# ---------------------------------------------------------------------------
# Core update logic
# ---------------------------------------------------------------------------

def update_file(client: GitHubClient, path: str, add_n: int, delete_n: int,
                dry_run: bool = False) -> dict:
    result = client.get_file(path)
    if result is None:
        print(f"  SKIP {path}: not found in repo (run `init` first)")
        return {"path": path, "ok": False, "error": "not found"}
    content, sha = result

    lines = [ln for ln in content.splitlines() if ln and not ln.startswith("#")]
    orig_count = len(lines)

    gen = ENTRY_GENERATORS[infer_type(path)]
    additions = gen(add_n)

    safe_delete = min(delete_n, max(0, len(lines) // 2))
    if safe_delete > 0:
        del_idx = set(random.sample(range(len(lines)), safe_delete))
        lines = [ln for i, ln in enumerate(lines) if i not in del_idx]

    lines.extend(additions)

    seen: set[str] = set()
    deduped: list[str] = []
    for ln in lines:
        s = ln.strip()
        if s and s not in seen:
            seen.add(s)
            deduped.append(s)

    new_count = len(deduped)
    stats = {
        "path": path,
        "type": infer_type(path),
        "orig": orig_count,
        "added": len(additions),
        "deleted": safe_delete,
        "final": new_count,
        "ok": True,
    }

    if dry_run:
        print(f"  [DRY-RUN] {path}: {orig_count} -> {new_count} "
              f"(+{len(additions)} -{safe_delete})")
        return stats

    header_lines = [ln for ln in content.splitlines() if ln.startswith("#")]
    final_content = "\n".join(header_lines + deduped) + "\n"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg = (f"edl-update({path}): "
           f"+{len(additions)} -{safe_delete} "
           f"[{orig_count}->{new_count}] {ts}")

    try:
        client.put_file(path, final_content, sha, msg)
        print(f"  OK  {path}: {orig_count:>7,} -> {new_count:>7,} "
              f"(+{len(additions)} -{safe_delete})")
    except requests.HTTPError as exc:
        stats.update({"ok": False, "error": str(exc)})
        print(f"  ERR {path}: {exc}")

    return stats


# ---------------------------------------------------------------------------
# `update` run cycle
# ---------------------------------------------------------------------------

def run_once(config: dict, add_n: int, delete_n: int, types: list[str],
             specific_file: str | None, dry_run: bool,
             inter_call_delay: float, config_path: str) -> dict:

    client = make_client(config, config_path)

    if specific_file:
        files = [specific_file]
    else:
        files = build_file_list(config, types)

    if not files:
        print("No files selected. Check config.yaml [lists] section.")
        return {"total": 0, "ok": 0, "failed": 0}

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tag = "[DRY-RUN] " if dry_run else ""
    print(f"\n{tag}[{ts}] Updating {len(files)} EDL objects "
          f"(+{add_n} / -{delete_n} each)")
    print()

    if not dry_run:
        rl = client.rate_limit()
        needed = len(files) * 2
        if rl["remaining"] < needed:
            reset = datetime.fromtimestamp(rl["reset"], tz=timezone.utc).strftime("%H:%M:%S UTC")
            print(f"  WARNING: rate limit low ({rl['remaining']} remaining, resets {reset})")

    results = []
    for fpath in files:
        stat = update_file(client, fpath, add_n, delete_n, dry_run)
        results.append(stat)
        if not dry_run and inter_call_delay > 0:
            time.sleep(inter_call_delay)

    ok      = sum(1 for r in results if r.get("ok"))
    failed  = len(results) - ok
    added   = sum(r.get("added", 0) for r in results)
    deleted = sum(r.get("deleted", 0) for r in results)
    print(f"\n  Done: {ok} OK / {failed} failed | "
          f"added {added:,} / deleted {deleted:,} entries total")
    return {"total": len(results), "ok": ok, "failed": failed,
            "added": added, "deleted": deleted}


# ---------------------------------------------------------------------------
# `init` — generate all EDL objects + push to GitHub
# ---------------------------------------------------------------------------

def push_all_files(client: GitHubClient, lists_dir: Path,
                   entries: int, seed: int, dry_run: bool) -> dict:
    """Generate all 20 EDL list files locally and push to GitHub."""
    random.seed(seed)
    ok = failed = 0

    for subdir, filename, gen_fn, gen_kwargs, header in INIT_MANIFEST:
        local_path = lists_dir / subdir / filename
        repo_path  = f"lists/{subdir}/{filename}"

        # Generate entries
        if gen_kwargs:
            raw = gen_fn(entries, **gen_kwargs)
        else:
            raw = gen_fn(entries)

        # Write locally
        _write(local_path, raw, header)

        size_kb = local_path.stat().st_size // 1024

        if dry_run:
            print(f"  [DRY-RUN] would push {repo_path}  "
                  f"({len(raw):,} entries, {size_kb} KB)")
            ok += 1
            continue

        # Get existing sha if file already exists
        existing = client.get_file(repo_path)
        sha = existing[1] if existing else None
        action = "update" if sha else "create"

        try:
            content = local_path.read_text(encoding="utf-8")
            client.put_file(repo_path, content, sha, f"init: {action} {repo_path}")
            print(f"  OK  [{action}] {repo_path}  ({len(raw):,} entries, {size_kb} KB)")
            ok += 1
        except requests.HTTPError as exc:
            print(f"  ERR          {repo_path}: {exc}")
            failed += 1

        time.sleep(0.4)  # rate-limit friendly

    return {"ok": ok, "failed": failed}


def cmd_init(args, config: dict, config_path: str) -> None:
    entries = args.entries
    seed    = args.seed

    print(f"EDL Manager — init")
    print(f"  Entries per file : {entries:,}")
    print(f"  Random seed      : {seed}")
    print(f"  GitHub repo      : {config['github']['repo']}")
    print(f"  Dry run          : {args.dry_run}")
    print()

    client = make_client(config, config_path)

    if not args.dry_run:
        rl = client.rate_limit()
        print(f"  Rate limit: {rl['remaining']}/{rl['limit']} remaining\n")

    result = push_all_files(client, LISTS_DIR, entries, seed, args.dry_run)
    total = result["ok"] + result["failed"]
    print(f"\nInit complete: {result['ok']}/{total} EDL objects pushed successfully.")


# ---------------------------------------------------------------------------
# `update` — random-subset update loop
# ---------------------------------------------------------------------------

def parse_interval(s: str) -> int:
    s = s.strip().lower()
    if s.endswith("m"):
        return int(s[:-1]) * 60
    if s.endswith("h"):
        return int(s[:-1]) * 3600
    if s.endswith("s"):
        return int(s[:-1])
    raise ValueError(f"Invalid interval '{s}'. Use '1m', '1h', '30s', etc.")


def cmd_update(args, config: dict, config_path: str) -> None:
    add_n    = args.add    or config["update"]["add_per_run"]
    delete_n = args.delete or config["update"]["delete_per_run"]

    print(f"EDL Manager — update")
    print(f"  Add/delete per file : +{add_n} / -{delete_n}")
    print(f"  Types               : {args.types}")
    print(f"  Interval            : {args.interval or 'single run'}")
    print(f"  Dry run             : {args.dry_run}")
    print()

    kwargs = dict(
        config=config,
        add_n=add_n,
        delete_n=delete_n,
        types=args.types,
        specific_file=args.file,
        dry_run=args.dry_run,
        inter_call_delay=args.delay,
        config_path=config_path,
    )

    if args.interval:
        interval_secs = parse_interval(args.interval)
        print(f"Scheduler: every {args.interval} ({interval_secs}s). Ctrl+C to stop.\n")
        iteration = 0
        while True:
            iteration += 1
            print(f"{'='*60}")
            print(f"Iteration #{iteration}")
            run_once(**kwargs)
            print(f"\nSleeping {interval_secs}s until next run...")
            try:
                time.sleep(interval_secs)
            except KeyboardInterrupt:
                print("\nStopped.")
                break
    else:
        run_once(**kwargs)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    root = argparse.ArgumentParser(
        description="EDL Manager — create and update EDL list objects in GitHub"
    )
    root.add_argument("--config", default=str(CONFIG_PATH),
                      help="Path to config.yaml")
    sub = root.add_subparsers(dest="cmd", required=True)

    # ---- init ----
    p_init = sub.add_parser("init",
        help="Generate all 20 EDL list files locally and push to GitHub")
    p_init.add_argument("--entries", type=int, default=20_000,
                        help="Entries per EDL object file (default: 20000)")
    p_init.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    p_init.add_argument("--dry-run", action="store_true",
                        help="Generate files locally but skip GitHub push")

    # ---- update ----
    p_upd = sub.add_parser("update",
        help="Randomly update a subset of EDL objects each run")
    p_upd.add_argument("--interval", metavar="INTERVAL",
                       help="Repeat interval: '1m', '1h', '30s'. Omit for single run.")
    p_upd.add_argument("--add", type=int, default=None,
                       help="Entries to add per file (overrides config)")
    p_upd.add_argument("--delete", type=int, default=None,
                       help="Entries to delete per file (overrides config)")
    p_upd.add_argument("--types", nargs="+", choices=["ip", "url", "domain"],
                       default=["ip", "url", "domain"],
                       help="Which list types to include (default: all)")
    p_upd.add_argument("--file", metavar="PATH",
                       help="Update a single specific file instead of a random subset")
    p_upd.add_argument("--dry-run", action="store_true",
                       help="Show selected files and projected changes; no GitHub writes")
    p_upd.add_argument("--delay", type=float, default=0.5,
                       help="Seconds between API calls (default: 0.5)")

    args = root.parse_args()
    config_path = args.config

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        print(f"ERROR: Config not found at {config_path}")
        sys.exit(1)

    if (not getattr(args, "dry_run", False)
            and config["github"]["token"] == "ghp_YOUR_TOKEN_HERE"):
        print("ERROR: Set your GitHub PAT in config.yaml → github.token")
        sys.exit(1)

    if args.cmd == "init":
        cmd_init(args, config, config_path)
    elif args.cmd == "update":
        cmd_update(args, config, config_path)


if __name__ == "__main__":
    main()
