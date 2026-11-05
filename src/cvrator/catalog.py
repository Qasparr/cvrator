# ============================================================================
# 93
# CVRATOR · catalog.py — one index over every house the steward keeps.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Method of Science, Aim of Religion.
#
# DOCTRINE: the providers stay many; the FINDING becomes one. Files are
# never striped or pooled across accounts — each file sits whole in one
# vault. What is unified is the catalog: name, size, hash, date and
# location of every file in every connected house, searchable at once.
# An empty search means "not indexed", never "does not exist".
# ============================================================================

import json
import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_DB = os.path.expanduser("~/.cvrator/catalog.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    provider TEXT, id TEXT, name TEXT, size INTEGER,
    hash TEXT, hash_alg TEXT, created TEXT, web_url TEXT,
    PRIMARY KEY (provider, id)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def _connect(db_path):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def build_catalog(db_path, provider_records, quotas=None):
    """MECHANISM: refresh the catalog rows for exactly the providers
    handed in (other providers' rows are left standing), and stamp the
    build time + each provider's quota into meta. Returns per-provider
    {files, bytes} plus a total."""
    conn = _connect(db_path)
    stats = {}
    with conn:
        for provider, records in provider_records.items():
            conn.execute("DELETE FROM files WHERE provider = ?",
                         (provider,))
            conn.executemany(
                "INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?,?)",
                [(r.provider, r.id, r.name, r.size or 0, r.hash,
                  r.hash_alg, r.created, r.web_url) for r in records])
            stats[provider] = {
                "files": len(records),
                "bytes": sum(r.size or 0 for r in records)}
            if quotas and provider in quotas:
                conn.execute(
                    "INSERT OR REPLACE INTO meta VALUES (?,?)",
                    (f"quota:{provider}", json.dumps(quotas[provider])))
        conn.execute("INSERT OR REPLACE INTO meta VALUES (?,?)",
                     ("built_at",
                      datetime.now(timezone.utc).isoformat()))
    conn.close()
    stats["total"] = {
        "files": sum(s["files"] for s in stats.values()),
        "bytes": sum(s["bytes"] for s in stats.values())}
    return stats


def catalog_stats(db_path):
    """MECHANISM: what the catalog currently holds, per provider."""
    if not os.path.exists(db_path):
        return None
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT provider, COUNT(*), COALESCE(SUM(size),0) FROM files "
        "GROUP BY provider ORDER BY provider").fetchall()
    built = conn.execute(
        "SELECT value FROM meta WHERE key = 'built_at'").fetchone()
    conn.close()
    per = {p: {"files": n, "bytes": b} for p, n, b in rows}
    per["total"] = {"files": sum(v["files"] for v in per.values()),
                    "bytes": sum(v["bytes"] for v in per.values())}
    return {"built_at": built[0] if built else None, "providers": per}


def search_catalog(db_path, query, limit=50):
    """MECHANISM: one substring search across every house at once."""
    if not os.path.exists(db_path):
        return []
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT provider, name, size, created, web_url FROM files "
        "WHERE name LIKE ? ORDER BY created LIMIT ?",
        (f"%{query}%", limit)).fetchall()
    conn.close()
    return [{"provider": p, "name": n, "size": s, "created": c,
             "web_url": u} for p, n, s, c, u in rows]

# 93 — Live, Love, and let Love, Live.
