# CVRATOR — API & Command Reference

> Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
> (Greek, -ARR, All Rights Reserved, Without Prejudice).
> Method of Science, Aim of Religion.

CVRATOR has two surfaces: the **CLI** (`cvrator`, also
`python3 -m cvrator`) and the **Python module API** for embedding.

## CLI

### `cvrator status [--provider all|gdrive|onedrive]`

Prints one JSON object per provider:
`{"provider": "gdrive", "state": "connected"}`.
OneDrive reports `not_configured` (with the env var it needs) when no
token is present.

### `cvrator quota [--provider all|gdrive|onedrive]`

Human-readable storage ledger per provider: used / limit, the in-drive
share, and the trash share. Source: Drive `about.get` storageQuota;
Graph `/me/drive` quota.

### `cvrator scan --provider gdrive|onedrive [--out DIR] [--verify]`

The census. Pages through every non-trashed file, groups byte-identical
duplicates by (hash algorithm, hash, size), picks the earliest-created
keeper per group, and writes into `DIR`:

- `<provider>-plan.json` — the plan: provider, generation time, quota,
  files seen, files without a hash, groups (keeper + duplicates, each
  with id/name/size/created/web URL), `verified_sha256` per group, and
  total `reclaimable_bytes`.
- `<provider>-plan.csv` — the same groups, one row per file, `role`
  column reading KEEPER or DUPLICATE.

`--verify` additionally downloads every keeper and duplicate and marks
a group `verified_sha256: true` only when all members share one SHA-256
digest over their real bytes. **Scan never removes anything**, with or
without `--verify`.

Exit codes: `0` ok · `2` provider not configured / refused.

### `cvrator trash --plan PLAN.json`

The only destructive verb, and it is trash, not delete:

1. Refuses unless **every** group in the plan is SHA-256 verified.
2. Prints the count and reclaimable bytes, then requires the operator
   to type exactly `TRASH n FILES`.
3. Moves each duplicate to the provider's trash (Drive:
   `trashed=true`, recoverable ~30 days; OneDrive: Graph DELETE, which
   lands in the recycle bin).

Permanent deletion is not implemented anywhere in this tool.

### `cvrator providers [--json]`

The roll of vaults: every known house with its free tier, automation
class (`official_api` / `official_cli` / `standard_protocol` /
`manual_only`), transport, and its caution — inactivity deletion,
per-file caps, transfer quotas — printed on its face.

### `cvrator catalog build [--provider all|gdrive|onedrive] [--db PATH]`

Censuses each readable provider into one SQLite catalog
(default `~/.cvrator/catalog.db`). Unconfigured providers are labelled
and skipped, never silently zeroed. Other providers' rows are left
standing on a partial rebuild.

### `cvrator catalog stats [--db PATH]` / `cvrator catalog search QUERY [--limit N]`

Stats: build stamp + per-provider and total files/bytes. Search: one
substring search across every house at once. No hits means *not
indexed*, never *does not exist*.

### `cvrator archive plan --provider gdrive|onedrive [--older-than-years 10] [--older-than-days N] [--out DIR]`

Names the cold set — files whose provider-reported creation date
precedes the cutoff (an upload date is not a birth date, and the plan
says so) — weighs it, and recommends ONE vault from the registry that
the whole set fits (preference: Filen, MEGA, Backblaze B2, local;
manual-only providers are never recommended). Writes
`archive-plan.json` + `archive-plan.csv`. **A plan moves nothing and
removes nothing.** The migration law for any later move: copy →
SHA-256 verify at the target → catalog entry → only then, as a
separate approved step, removal at the source.

## Python module API

```python
from cvrator.model import FileRecord, build_groups, human
from cvrator.gdrive import GoogleDriveProvider
from cvrator.onedrive import OneDriveProvider, NotConfigured
```

- `FileRecord(provider, id, name, size, hash, hash_alg, created, web_url)`
  — the one record shape both providers translate into.
- `build_groups(records) -> (groups, reclaimable_bytes, stats)` — the
  grouping law: buckets on (hash_alg, hash, size); hash-less records are
  counted in `stats["no_hash"]` and skipped.
- Provider interface (both providers):
  - `status() -> dict`
  - `quota() -> {limit, usage, usage_in_drive, usage_in_trash}` (bytes)
  - `list_files() -> [FileRecord]` (complete census, folders excluded)
  - `download(file_id, dest_path)`
  - `trash(file_id) -> True`

- `cvrator.registry.REGISTRY` — the roll of vaults (`ProviderInfo`:
  free tier, automation class, transport, per-file cap, inactivity
  days, zero-knowledge, verdict, caution).
  `recommend_target(total_bytes, largest_file, source_key)` picks one
  whole-set vault or explains every closed door.
- `cvrator.catalog` — `build_catalog(db, {provider: [FileRecord]},
  quotas)`, `catalog_stats(db)`, `search_catalog(db, query)`.
- `cvrator.archive` — `select_candidates(records, years, days, now)`,
  `make_plan(records, source_key, ...)` → the archive plan dict,
  migration law included.

## Environment variables

| Variable | Used by | Meaning |
|---|---|---|
| `CVRATOR_ONEDRIVE_ACCESS_TOKEN` | OneDrive provider | A Microsoft Graph access token from the operator's own app registration (scope `Files.ReadWrite`). Never stored, never printed. |

## Safety invariants (enforced in code, not just documented)

- No command except `trash` can modify an account.
- `trash` cannot run on an unverified plan, cannot run without the
  typed phrase, and has no permanent-delete code path.
- Hashes are compared only within one provider + one algorithm.
