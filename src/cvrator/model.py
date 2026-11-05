# ============================================================================
# 93
# CVRATOR · model.py — the provider-neutral record and the grouping law.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Method of Science, Aim of Religion.
#
# MECHANISM: every provider (Google Drive today, OneDrive by Graph)
# translates its native file objects into ONE record shape, so the
# duplicate law is written once and judged identically in both houses.
#
# DOCTRINE: byte-identical means byte-identical. A duplicate group exists
# only where size AND the provider's content hash agree. Names are never
# evidence. Records without a hash are counted and skipped, never guessed.
# The keeper of a group is its earliest-created member (ties: name, id);
# the first instance is the ancestor, the rest are echoes.
# ============================================================================

from dataclasses import dataclass, field, asdict
from collections import defaultdict


@dataclass
class FileRecord:
    provider: str          # 'gdrive' | 'onedrive'
    id: str
    name: str
    size: int
    hash: str = ""         # provider content hash ('' when none exists)
    hash_alg: str = ""     # 'md5' | 'sha1' | 'quickXor' | ...
    created: str = ""      # ISO-8601, provider-reported
    web_url: str = ""

    def slim(self):
        return asdict(self)


def human(n):
    """MECHANISM: bytes -> the shortest honest human denomination."""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1024


def build_groups(records):
    """MECHANISM: group on (hash_alg, hash, size) WITHIN one provider —
    hashes are only comparable inside the house that minted them.
    Returns (groups, stats); each group carries keeper + duplicates."""
    buckets = defaultdict(list)
    stats = {"seen": 0, "no_hash": 0}
    for r in records:
        stats["seen"] += 1
        if not r.hash:
            stats["no_hash"] += 1
            continue
        buckets[(r.hash_alg, r.hash, r.size)].append(r)

    groups, reclaimable = [], 0
    for (alg, h, size), members in buckets.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda r: (r.created, r.name, r.id))
        keeper, extras = members[0], members[1:]
        reclaimable += size * len(extras)
        groups.append({
            "hash_alg": alg, "hash": h, "size": size,
            "keeper": keeper.slim(),
            "duplicates": [e.slim() for e in extras],
            "verified_sha256": False,
        })
    groups.sort(key=lambda g: -g["size"] * len(g["duplicates"]))
    return groups, reclaimable, stats
