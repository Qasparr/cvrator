# ============================================================================
# 93
#
# "Do what thou wilt shall be the whole of the Law."
#
# CVRATOR — steward of cloud stores.
# A Scientific Illuminist treatment of duplicate custody across
# Google Drive and OneDrive: observe everything, claim nothing the
# checksum does not prove, and destroy nothing on a first pass.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# V day of November, Dies Iovis, Sol in Scorpio, Anno V:xii e.n. (2026 e.v.)
#
# Classification: Enterprise • Educational • Research & Development
# Method of Science, Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice. Right of claim hereby reserved and
# coined under the authority of the Living Man.
#
# ----------------------------------------------------------------------------
# CONTENT TEST (the four-element engineering spec)
#   Inputs:    one or both provider accounts (Google Drive through the
#              house connector; OneDrive through Microsoft Graph + the
#              operator's own token).
#   Processes: census -> group by (hash, size) -> choose one keeper per
#              group -> optional SHA-256 verification over real bytes ->
#              guarded trash of the extras, from a saved plan only.
#   Outputs:   status, quota, duplicate plans (JSON + CSV) and reports.
#   Tolerances: scan and verify NEVER remove anything. Trash fires only
#              from a fully SHA-256-verified plan, only after the exact
#              confirmation phrase is typed, and only into each
#              provider's recoverable trash/recycle bin. Permanent
#              deletion is deliberately NOT implemented.
# ----------------------------------------------------------------------------
# Commands:
#   cvrator status [--provider gdrive|onedrive|all]
#   cvrator quota  [--provider ...]
#   cvrator scan   --provider gdrive [--out DIR] [--verify]
#   cvrator trash  --plan PLAN.json          (typed confirmation)
#   cvrator providers [--json]               (the roll of vaults)
#   cvrator catalog build|stats|search ...   (one index, every house)
#   cvrator archive plan --provider gdrive [--older-than-years 10]
#                                            (plans only; moves nothing)
# ============================================================================

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

from . import __version__
from .model import build_groups, human
from .gdrive import GoogleDriveProvider
from .onedrive import OneDriveProvider, NotConfigured
from .registry import REGISTRY
from .catalog import (DEFAULT_DB, build_catalog, catalog_stats,
                      search_catalog)
from .archive import make_plan

PROVIDERS = {"gdrive": GoogleDriveProvider, "onedrive": OneDriveProvider}


def get_provider(name):
    return PROVIDERS[name]()


def cmd_status(args):
    names = list(PROVIDERS) if args.provider == "all" else [args.provider]
    for n in names:
        print(json.dumps(get_provider(n).status()))
    return 0


def cmd_quota(args):
    names = list(PROVIDERS) if args.provider == "all" else [args.provider]
    for n in names:
        try:
            q = get_provider(n).quota()
            print(f"{n}: used {human(q['usage'])} of {human(q['limit'])} "
                  f"(in-drive {human(q['usage_in_drive'])}, "
                  f"trash {human(q['usage_in_trash'])})")
        except NotConfigured as e:
            print(f"{n}: NOT CONFIGURED — {e}")
        except Exception as e:
            print(f"{n}: error — {e}")
    return 0


def _sha256_of(provider, file_id, workdir):
    path = os.path.join(workdir, file_id.replace("/", "_"))
    provider.download(file_id, path)
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    os.remove(path)
    return h.hexdigest()


def verify_groups(provider, groups, workdir):
    """MECHANISM: re-prove each group over its actual bytes. A group is
    verified only when keeper + every duplicate hash to one SHA-256."""
    for g in groups:
        digests = {_sha256_of(provider, m["id"], workdir)
                   for m in [g["keeper"]] + g["duplicates"]}
        g["verified_sha256"] = (len(digests) == 1)
    return groups


def cmd_scan(args):
    provider = get_provider(args.provider)
    try:
        quota = provider.quota()
        records = provider.list_files()
    except NotConfigured as e:
        print(f"{args.provider}: NOT CONFIGURED — {e}", file=sys.stderr)
        return 2
    groups, reclaimable, stats = build_groups(records)
    if args.verify and groups:
        with tempfile.TemporaryDirectory() as td:
            groups = verify_groups(provider, groups, td)
    plan = {
        "tool": "cvrator", "version": __version__,
        "provider": args.provider,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quota": quota,
        "files_seen": stats["seen"],
        "files_without_hash": stats["no_hash"],
        "groups": groups,
        "reclaimable_bytes": reclaimable,
    }
    os.makedirs(args.out, exist_ok=True)
    plan_path = os.path.join(args.out, f"{args.provider}-plan.json")
    with open(plan_path, "w") as fh:
        json.dump(plan, fh, indent=2)
    csv_path = os.path.join(args.out, f"{args.provider}-plan.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["provider", "hash_alg", "hash", "size_bytes", "role",
                    "name", "created", "web_url"])
        for g in groups:
            for role, m in [("KEEPER", g["keeper"])] + [
                    ("DUPLICATE", d) for d in g["duplicates"]]:
                w.writerow([args.provider, g["hash_alg"], g["hash"],
                            g["size"], role, m["name"], m["created"],
                            m["web_url"]])
    print(f"{args.provider}: scanned {stats['seen']:,} files "
          f"({stats['no_hash']:,} without a hash, skipped by the law).")
    print(f"{len(groups)} duplicate groups | reclaimable "
          f"{human(reclaimable)} | plan: {plan_path}")
    return 0


def cmd_trash(args):
    with open(args.plan) as fh:
        plan = json.load(fh)
    groups = plan["groups"]
    if not groups:
        print("plan holds no duplicate groups. Nothing to do.")
        return 0
    if not all(g.get("verified_sha256") for g in groups):
        print("REFUSED: every group in the plan must be SHA-256 verified "
              "first (re-run: cvrator scan --verify). Nothing trashed.",
              file=sys.stderr)
        return 2
    provider = get_provider(plan["provider"])
    extras = [d for g in groups for d in g["duplicates"]]
    phrase = f"TRASH {len(extras)} FILES"
    print(f"This moves {len(extras)} duplicate files to "
          f"{plan['provider']}'s trash/recycle bin "
          f"({human(plan['reclaimable_bytes'])}), keeping one verified "
          f"copy of each. Recoverable. Type exactly: {phrase}")
    if input("> ").strip() != phrase:
        print("phrase not matched. Nothing trashed.")
        return 1
    for d in extras:
        try:
            provider.trash(d["id"])
            print(f"trashed: {d['name']}")
        except Exception as e:
            print(f"FAILED: {d['name']} — {e}")
    return 0


def cmd_providers(args):
    infos = list(REGISTRY.values())
    if args.json:
        print(json.dumps([i.slim() for i in infos], indent=2))
        return 0
    for i in infos:
        free = human(i.free_bytes) if i.free_bytes else "media's own"
        print(f"{i.key:13} {i.name:28} free {free:>11} | "
              f"{i.automation} ({i.transport})")
        print(f"{'':13} {i.verdict}. {i.caution}")
    return 0


def cmd_catalog_build(args):
    names = list(PROVIDERS) if args.provider == "all" else [args.provider]
    records_by, quotas = {}, {}
    for n in names:
        prov = get_provider(n)
        try:
            records_by[n] = prov.list_files()
            quotas[n] = prov.quota()
        except NotConfigured as e:
            print(f"{n}: NOT CONFIGURED — skipped in the catalog ({e})")
        except Exception as e:
            print(f"{n}: error — skipped in the catalog ({e})")
    if not records_by:
        print("no provider could be read. Catalog unchanged.",
              file=sys.stderr)
        return 2
    stats = build_catalog(args.db, records_by, quotas)
    for n, s in stats.items():
        if n != "total":
            print(f"{n}: {s['files']:,} files, {human(s['bytes'])} "
                  f"entered in the catalog")
    t = stats["total"]
    print(f"catalog: {t['files']:,} files, {human(t['bytes'])} across "
          f"{len(records_by)} house(s) | db: {args.db}")
    return 0


def cmd_catalog_stats(args):
    st = catalog_stats(args.db)
    if not st:
        print(f"no catalog at {args.db} yet — run: cvrator catalog build")
        return 0
    print(f"catalog built: {st['built_at']}")
    for n, s in st["providers"].items():
        label = "TOTAL" if n == "total" else n
        print(f"{label}: {s['files']:,} files, {human(s['bytes'])}")
    return 0


def cmd_catalog_search(args):
    rows = search_catalog(args.db, args.query, limit=args.limit)
    if not rows:
        print("(no hits in the catalog — not indexed is not nonexistent)")
        return 0
    for r in rows:
        print(f"{r['provider']:9} {(r['created'] or '')[:10]:10} "
              f"{human(r['size'] or 0):>10}  {r['name']}")
    return 0


def cmd_archive_plan(args):
    provider = get_provider(args.provider)
    try:
        records = provider.list_files()
    except NotConfigured as e:
        print(f"{args.provider}: NOT CONFIGURED — {e}", file=sys.stderr)
        return 2
    plan = make_plan(records, args.provider,
                     years=args.older_than_years,
                     days=args.older_than_days)
    os.makedirs(args.out, exist_ok=True)
    plan_path = os.path.join(args.out, "archive-plan.json")
    with open(plan_path, "w") as fh:
        json.dump(plan, fh, indent=2)
    csv_path = os.path.join(args.out, "archive-plan.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "id", "name", "size_bytes", "created",
                    "web_url", "target"])
        tgt = plan["target"]["key"] if plan["target"] else ""
        for c in plan["candidates"]:
            w.writerow([args.provider, c["id"], c["name"], c["size"],
                        c["created"], c["web_url"], tgt])
    print(f"{args.provider}: {plan['files_seen']:,} files seen; "
          f"{len(plan['candidates'])} cold ({plan['rule']}, before "
          f"{plan['cutoff'][:10]}); {plan['skipped_no_date']} without a "
          f"date, counted apart.")
    print(f"cold set: {human(plan['total_bytes'])} | plan: {plan_path}")
    if plan["target"]:
        t = plan["target"]
        print(f"recommended vault: {t['name']} ({t['key']}) — "
              f"{t['reason']}")
    print("PLAN ONLY — nothing moved, nothing removed.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="cvrator",
        description="CVRATOR — steward of cloud stores: byte-identical "
                    "duplicate management, a unified catalog over every "
                    "house, and cold-file archive planning across "
                    "Google Drive, OneDrive and the wider roll of vaults.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="provider connection status")
    p.add_argument("--provider", default="all",
                   choices=["all", "gdrive", "onedrive"])
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("quota", help="storage quota per provider")
    p.add_argument("--provider", default="all",
                   choices=["all", "gdrive", "onedrive"])
    p.set_defaults(fn=cmd_quota)

    p = sub.add_parser("scan", help="census + duplicate plan (no removal)")
    p.add_argument("--provider", required=True,
                   choices=["gdrive", "onedrive"])
    p.add_argument("--out", default="reports")
    p.add_argument("--verify", action="store_true",
                   help="SHA-256-verify every group over its real bytes")
    p.set_defaults(fn=cmd_scan)

    p = sub.add_parser("trash", help="trash a verified plan's duplicates")
    p.add_argument("--plan", required=True)
    p.set_defaults(fn=cmd_trash)

    p = sub.add_parser("providers", help="the roll of known vaults")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_providers)

    p = sub.add_parser("catalog", help="one index over every house")
    csub = p.add_subparsers(dest="catalog_cmd", required=True)
    cp = csub.add_parser("build", help="census providers into the catalog")
    cp.add_argument("--provider", default="all",
                    choices=["all", "gdrive", "onedrive"])
    cp.add_argument("--db", default=DEFAULT_DB)
    cp.set_defaults(fn=cmd_catalog_build)
    cp = csub.add_parser("stats", help="what the catalog holds")
    cp.add_argument("--db", default=DEFAULT_DB)
    cp.set_defaults(fn=cmd_catalog_stats)
    cp = csub.add_parser("search", help="search every house at once")
    cp.add_argument("query")
    cp.add_argument("--db", default=DEFAULT_DB)
    cp.add_argument("--limit", type=int, default=50)
    cp.set_defaults(fn=cmd_catalog_search)

    p = sub.add_parser("archive", help="cold-file planning (moves nothing)")
    asub = p.add_subparsers(dest="archive_cmd", required=True)
    ap2 = asub.add_parser("plan", help="name the cold set + a vault for it")
    ap2.add_argument("--provider", required=True,
                     choices=["gdrive", "onedrive"])
    ap2.add_argument("--older-than-years", type=float, default=10.0)
    ap2.add_argument("--older-than-days", type=int, default=None)
    ap2.add_argument("--out", default="reports")
    ap2.set_defaults(fn=cmd_archive_plan)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# Colophon: generated under the Doctrine, exclusive authorship as above,
# ARR/WP. Method of Science. Aim of Religion.
#
# Flagpole of Claim and Coinage: Johnathan 'Qasparr' Monroe, ARR, All
# Rights Reserved, Without Prejudice.
#
# 93 — Live, Love, and let Love, Live.
# ============================================================================
