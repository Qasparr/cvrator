# ============================================================================
# 93
# CVRATOR · registry.py — the roll of vaults the steward knows.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Method of Science, Aim of Religion.
#
# DOCTRINE: a free tier is a fact with conditions, never a promise.
# Every entry carries the conditions that can kill an archive —
# inactivity deletion, per-file caps, transfer quotas, a missing API —
# on its face, where the planner must reckon with them. A provider with
# no official automation door is MANUAL ONLY: CVRATOR will list it,
# warn about it, and never build a move on a reverse-engineered door.
#
# The name holds at this scope by its own meaning: a curator's charge
# was never one room. It is the whole household's goods, wherever kept.
# ============================================================================

from dataclasses import dataclass, asdict

GB = 1024 ** 3
MB = 1024 ** 2


@dataclass
class ProviderInfo:
    key: str
    name: str
    free_bytes: int = None        # None = no fixed free quota (e.g. local)
    automation: str = "manual_only"  # official_api | official_cli |
                                     # standard_protocol | manual_only
    transport: str = ""
    max_file_bytes: int = None    # None = no known per-file cap
    inactivity_days: int = None   # None = no known inactivity deletion
    zero_knowledge: bool = False
    verdict: str = ""
    caution: str = ""

    def slim(self):
        return asdict(self)


REGISTRY = {p.key: p for p in [
    ProviderInfo(
        "gdrive", "Google Drive", free_bytes=15 * GB,
        automation="official_api", transport="house connector / Drive API",
        verdict="Source house (live in this tool)",
        caution="The 15 GB is the whole Google account: Drive, Gmail "
                "and Photos share one ledger."),
    ProviderInfo(
        "onedrive", "OneDrive", free_bytes=5 * GB,
        automation="official_api", transport="Microsoft Graph",
        verdict="Second house (live when configured)",
        caution="In this house it needs the operator's own Graph token."),
    ProviderInfo(
        "filen", "Filen", free_bytes=10 * GB,
        automation="official_api",
        transport="CLI / SDK / WebDAV / S3 gateway",
        zero_knowledge=True, verdict="First archive candidate",
        caution="Zero-knowledge: guard the recovery key — no one can "
                "reset your way back to the bytes."),
    ProviderInfo(
        "mega", "MEGA", free_bytes=20 * GB,
        automation="official_cli", transport="MEGAcmd / API",
        zero_knowledge=True, verdict="Largest free vault",
        caution="Free accounts face transfer quotas; keep the account "
                "active."),
    ProviderInfo(
        "pcloud", "pCloud", free_bytes=10 * GB,
        automation="official_api", transport="pCloud API",
        verdict="Capable general vault",
        caution="Zero-knowledge Crypto is a paid add-on; the free tier "
                "is readable by the provider."),
    ProviderInfo(
        "backblaze_b2", "Backblaze B2", free_bytes=10 * GB,
        automation="standard_protocol", transport="S3-compatible API",
        verdict="Archive-grade object storage",
        caution="Built for machines, not browsing; an archive's "
                "archive."),
    ProviderInfo(
        "degoo", "Degoo", free_bytes=20 * GB,
        automation="manual_only", transport="app / web only — no "
        "official API", max_file_bytes=256 * MB, inactivity_days=90,
        verdict="REJECTED as an archive vault",
        caution="Free accounts are deleted after ~90 days inactive and "
                "files cap at ~256 MB. Manual extra bucket at most; "
                "never a sole copy, never automated here."),
    ProviderInfo(
        "local", "Local media (SD / USB / disk)", free_bytes=None,
        automation="standard_protocol", transport="filesystem",
        verdict="The vault in your hand",
        caution="Capacity is the medium's own; one device is one point "
                "of failure — pair it with one cloud vault."),
]}

# Preference order for an archive target: automated, survivable, roomy.
TARGET_PREFERENCE = ["filen", "mega", "backblaze_b2", "local"]


def recommend_target(total_bytes, largest_file, source_key=None):
    """MECHANISM: choose ONE vault for a set of whole files. A file is
    never split across vaults; the catalog, not the bytes, is what gets
    unified. Manual-only providers are never recommended. Returns a
    dict with the chosen key and the reasons every other door closed."""
    rejected = {}
    for key in TARGET_PREFERENCE:
        if key == source_key:
            continue
        info = REGISTRY[key]
        if info.max_file_bytes and largest_file > info.max_file_bytes:
            rejected[key] = (f"largest file exceeds its "
                             f"{info.max_file_bytes // MB} MB cap")
            continue
        if info.free_bytes is not None and total_bytes > info.free_bytes:
            rejected[key] = "the set does not fit its free tier"
            continue
        return {"key": key, "name": info.name,
                "reason": "first automated vault, in preference order, "
                          "that the whole set fits",
                "rejected_before_it": rejected}
    return {"key": "local", "name": REGISTRY["local"].name,
            "reason": "no free cloud tier holds the whole set; local "
                      "media has no quota wall",
            "rejected_before_it": rejected}

# 93 — Live, Love, and let Love, Live.
