# ============================================================================
# 93
# CVRATOR · archive.py — the cold-file planner.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Method of Science, Aim of Religion.
#
# DOCTRINE: a plan moves nothing. The planner names the cold files
# (older than the operator's line — ten years by his standing rule),
# weighs them, and places them across EVERY usable vault in the roll
# at once — his correction of the desk's first design, which made a
# dilemma of doors that were never rivals. Placement is whole-file
# only: a file lives in exactly one vault; what is shared is the
# catalog and the management, never the bytes of a single file.
# Any later move obeys the migration law:
#   copy -> SHA-256 verify at the target -> catalog entry ->
#   only then, as a separate approved step, removal at the source.
# A file is never split across vaults, and a manual-only provider
# (Degoo) is never a move target.
# ============================================================================

from datetime import datetime, timedelta, timezone

from .registry import REGISTRY, recommend_target

# The whole roll, in the order the steward fills it.
ALLOCATION_ORDER = ["filen", "mega", "pcloud", "backblaze_b2", "local"]


def allocate(records, source_key=None, include_manual=False,
             use_local=True):
    """MECHANISM: whole-file placement across every usable vault.
    Largest files are placed first (first-fit, preference order), each
    into the first vault whose remaining free tier and per-file cap
    admit it. Capacities are the published free-tier sizes; a connected
    account will replace them with measured free space. Manual-only
    vaults (Degoo) join the roll ONLY when include_manual is set, are
    marked mode=manual, and still obey their caps. Returns
    (allocations, unassigned)."""
    vaults = []
    for key in ALLOCATION_ORDER:
        if key == source_key:
            continue
        if key == "local" and not use_local:
            continue
        info = REGISTRY[key]
        vaults.append({"key": key, "name": info.name, "mode": "automated",
                       "capacity": info.free_bytes,
                       "remaining": info.free_bytes,
                       "max_file": info.max_file_bytes, "files": []})
    if include_manual:
        info = REGISTRY["degoo"]
        vaults.append({"key": "degoo", "name": info.name, "mode": "manual",
                       "capacity": info.free_bytes,
                       "remaining": info.free_bytes,
                       "max_file": info.max_file_bytes, "files": []})
    unassigned = []
    for r in sorted(records, key=lambda r: -(r.size or 0)):
        for v in vaults:
            if v["max_file"] and (r.size or 0) > v["max_file"]:
                continue
            if v["remaining"] is not None \
                    and (r.size or 0) > v["remaining"]:
                continue
            v["files"].append(r)
            if v["remaining"] is not None:
                v["remaining"] -= (r.size or 0)
            break
        else:
            unassigned.append(r)
    allocations = [{"key": v["key"], "name": v["name"], "mode": v["mode"],
                    "capacity_bytes": v["capacity"],
                    "bytes": sum(x.size or 0 for x in v["files"]),
                    "files": [x.slim() for x in v["files"]]}
                   for v in vaults if v["files"]]
    return allocations, unassigned


def parse_created(value):
    """MECHANISM: provider ISO-8601 -> aware datetime, or None."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def select_candidates(records, years=10.0, days=None, now=None):
    """MECHANISM: the cold set = files whose provider-reported creation
    precedes the cutoff. Age is reckoned on the provider's date and
    labelled as such — an upload date is not a birth date. Records with
    no parseable date are counted, never silently dropped."""
    now = now or datetime.now(timezone.utc)
    span = timedelta(days=days) if days is not None \
        else timedelta(days=years * 365.25)
    cutoff = now - span
    cold, skipped = [], 0
    for r in records:
        dt = parse_created(r.created)
        if dt is None:
            skipped += 1
            continue
        if dt < cutoff:
            cold.append(r)
    cold.sort(key=lambda r: (r.created, r.name))
    return {"cutoff": cutoff.isoformat(), "records": cold,
            "total_bytes": sum(r.size or 0 for r in cold),
            "skipped_no_date": skipped, "files_seen": len(records)}


def make_plan(records, source_key, years=10.0, days=None, now=None,
              include_manual=False, use_local=True):
    """MECHANISM: selection + placement across every usable vault.
    The plan also keeps `target` — the single-vault answer — for
    reference, so the old question stays answerable; but the plan's
    operative word is the allocation, not the target."""
    from . import __version__
    sel = select_candidates(records, years=years, days=days, now=now)
    allocations, unassigned = allocate(
        sel["records"], source_key=source_key,
        include_manual=include_manual, use_local=use_local)
    largest = max((r.size or 0 for r in sel["records"]), default=0)
    target = recommend_target(sel["total_bytes"], largest,
                              source_key=source_key) \
        if sel["records"] else None
    rule = (f"older than {days} days" if days is not None
            else f"older than {years:g} years")
    return {
        "tool": "cvrator", "version": __version__, "kind": "archive-plan",
        "source": source_key, "rule": rule,
        "cutoff": sel["cutoff"],
        "files_seen": sel["files_seen"],
        "skipped_no_date": sel["skipped_no_date"],
        "candidates": [r.slim() for r in sel["records"]],
        "total_bytes": sel["total_bytes"],
        "allocations": allocations,
        "unassigned": [r.slim() for r in unassigned],
        "target": target,
        "assumptions": [
            "capacities are published free-tier sizes; a connected "
            "account replaces them with measured free space",
            "every file is placed whole in exactly one vault; nothing "
            "is striped or split across accounts",
            "manual vaults (Degoo) appear only with include_manual, "
            "are never a sole copy, and obey their printed cautions",
        ],
        "law": "PLAN ONLY — nothing is moved or removed by a plan. A "
               "move is: copy -> SHA-256 verify at the target -> "
               "catalog entry -> only then, as a separate approved "
               "step, removal at the source.",
    }

# 93 — Live, Love, and let Love, Live.
