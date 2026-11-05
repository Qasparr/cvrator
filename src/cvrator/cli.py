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
# ============================================================================

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

from .model import build_groups, human
from .gdrive import GoogleDriveProvider
from .onedrive import OneDriveProvider, NotConfigured

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
        "tool": "cvrator", "version": "0.1.0",
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


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="cvrator",
        description="CVRATOR — steward of cloud stores: byte-identical "
                    "duplicate management for Google Drive and OneDrive.")
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
