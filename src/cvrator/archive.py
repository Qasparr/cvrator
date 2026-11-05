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
# weighs them, and recommends ONE vault from the registry that the
# whole set fits. Any later move obeys the migration law:
#   copy -> SHA-256 verify at the target -> catalog entry ->
#   only then, as a separate approved step, removal at the source.
# A file is never split across vaults, and a manual-only provider
# (Degoo) is never a move target.
# ============================================================================

from datetime import datetime, timedelta, timezone

from .registry import recommend_target


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


def make_plan(records, source_key, years=10.0, days=None, now=None):
    """MECHANISM: selection + one recommended vault = the plan."""
    from . import __version__
    sel = select_candidates(records, years=years, days=days, now=now)
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
        "target": target,
        "law": "PLAN ONLY — nothing is moved or removed by a plan. A "
               "move is: copy -> SHA-256 verify at the target -> "
               "catalog entry -> only then, as a separate approved "
               "step, removal at the source.",
    }

# 93 — Live, Love, and let Love, Live.
