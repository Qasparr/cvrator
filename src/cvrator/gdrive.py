# ============================================================================
# 93
# CVRATOR · gdrive.py — the Google Drive provider.
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Method of Science, Aim of Religion.
#
# MECHANISM: this provider speaks to Drive ONLY through the house
# connector CLI (/opt/hatch/bin/hatch_gws_cli), so the account's own
# connection, permissions, and approval flow govern CVRATOR exactly as
# they govern the desk. No credentials are read, stored, or handled here.
#
# DOCTRINE: Drive reports an MD5 checksum for stored binary files.
# Google-native files (Docs/Sheets/Slides) report none; they are counted
# and skipped by the grouping law, never guessed at. Removal is TRASH
# ONLY (files update trashed=true) — recoverable, never a hard delete.
# ============================================================================

import json
import subprocess

from .model import FileRecord

CLI = "/opt/hatch/bin/hatch_gws_cli"
FIELDS = ("files(id,name,mimeType,size,md5Checksum,createdTime,"
          "modifiedTime,parents,webViewLink),nextPageToken")
FOLDER_MIME = "application/vnd.google-apps.folder"


def _run(args, params=None, extra=None):
    cmd = [CLI] + args
    if params is not None:
        cmd += ["--params", json.dumps(params)]
    if extra:
        cmd += extra
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"connector CLI failed: {out.stderr.strip()[:300]}")
    return out.stdout


def _run_json(args, params=None):
    return json.loads(_run(args, params))


class GoogleDriveProvider:
    name = "gdrive"

    def status(self):
        try:
            s = _run_json(["drive", "status"])
            return {"provider": self.name,
                    "state": s.get("status", "unknown")}
        except Exception as e:  # connection problems are data, not crashes
            return {"provider": self.name, "state": f"error: {e}"}

    def quota(self):
        about = _run_json(["drive", "about", "get"],
                          {"fields": "storageQuota"})
        q = about.get("storageQuota", {})
        return {"limit": int(q.get("limit", 0)),
                "usage": int(q.get("usage", 0)),
                "usage_in_drive": int(q.get("usageInDrive", 0)),
                "usage_in_trash": int(q.get("usageInDriveTrash", 0))}

    def list_files(self):
        """MECHANISM: follow nextPageToken to exhaustion — a census,
        not a sample. Folders are skipped here and counted upstream."""
        records, token = [], None
        while True:
            params = {"pageSize": 1000, "q": "trashed=false",
                      "fields": FIELDS}
            if token:
                params["pageToken"] = token
            page = _run_json(["drive", "files", "list"], params)
            for f in page.get("files", []):
                if f.get("mimeType") == FOLDER_MIME:
                    continue
                records.append(FileRecord(
                    provider=self.name,
                    id=f["id"],
                    name=f.get("name", ""),
                    size=int(f.get("size", 0) or 0),
                    hash=f.get("md5Checksum", "") or "",
                    hash_alg="md5" if f.get("md5Checksum") else "",
                    created=f.get("createdTime", ""),
                    web_url=f.get("webViewLink", ""),
                ))
            token = page.get("nextPageToken")
            if not token:
                return records

    def download(self, file_id, dest_path):
        _run(["drive", "files", "get"],
             {"fileId": file_id, "alt": "media"},
             extra=["--output", dest_path])

    def trash(self, file_id):
        _run(["drive", "files", "update"], {"fileId": file_id},
             extra=["--json", json.dumps({"trashed": True})])
        return True
