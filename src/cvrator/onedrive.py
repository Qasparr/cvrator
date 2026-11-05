# ============================================================================
# 93
# CVRATOR · onedrive.py — the OneDrive provider (Microsoft Graph).
#
# Authorship attributed exclusively to Johnathan 'Qasparr' Monroe
# (Greek, -ARR, All Rights Reserved, Without Prejudice).
# Method of Science, Aim of Religion.
#
# MECHANISM: Microsoft Graph over HTTPS, standard library only.
#   GET  /v1.0/me/drive                  -> quota
#   GET  /v1.0/me/drive/root/children    -> listing (recursive, paged)
#   GET  /v1.0/me/drive/items/{id}/content -> download (for --verify)
#   DELETE /v1.0/me/drive/items/{id}     -> moves the item to the
#        OneDrive recycle bin (recoverable), which is this house's
#        trash-only doctrine expressed in Graph's own verb.
#
# DOCTRINE: there is no house OneDrive connector, so this provider takes
# its key from the operator's own hand: an access token in the
# environment variable CVRATOR_ONEDRIVE_ACCESS_TOKEN (obtained by the
# operator through Microsoft's own sign-in/device-code flow for their
# own app registration). CVRATOR never stores the token, never writes it
# to disk, and never prints it. Without a token the provider reports
# NOT CONFIGURED and refuses work — a labelled door, not a fake wall.
#
# Hash note: Graph reports file hashes (sha1Hash and/or quickXorHash in
# the file facet's hashes). Groups are formed within OneDrive only —
# a Graph hash is never compared against a Drive MD5.
# ============================================================================

import json
import os
import urllib.request
import urllib.error

from .model import FileRecord

GRAPH = "https://graph.microsoft.com/v1.0"
TOKEN_ENV = "CVRATOR_ONEDRIVE_ACCESS_TOKEN"


class NotConfigured(RuntimeError):
    pass


class OneDriveProvider:
    name = "onedrive"

    def __init__(self):
        self.token = os.environ.get(TOKEN_ENV, "")

    def _require(self):
        if not self.token:
            raise NotConfigured(
                f"{TOKEN_ENV} is not set. Obtain a Microsoft Graph access "
                "token for your own app registration (scopes: "
                "Files.ReadWrite, offline_access) via Microsoft's "
                "device-code sign-in, export it in this variable, and "
                "re-run. CVRATOR does not store tokens.")

    def _req(self, method, url, raw=False):
        self._require()
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Graph {method} {url} -> HTTP {e.code}")
        return body if raw else json.loads(body or b"{}")

    def status(self):
        if not self.token:
            return {"provider": self.name, "state": "not_configured",
                    "needs": TOKEN_ENV}
        try:
            self._req("GET", f"{GRAPH}/me/drive?$select=id")
            return {"provider": self.name, "state": "connected"}
        except Exception as e:
            return {"provider": self.name, "state": f"error: {e}"}

    def quota(self):
        d = self._req("GET", f"{GRAPH}/me/drive?$select=quota")
        q = d.get("quota", {})
        return {"limit": int(q.get("total", 0)),
                "usage": int(q.get("used", 0)),
                "usage_in_drive": int(q.get("used", 0)),
                "usage_in_trash": int(q.get("deleted", 0))}

    def _children(self, url):
        while url:
            page = self._req("GET", url)
            yield from page.get("value", [])
            url = page.get("@odata.nextLink")

    def list_files(self):
        """MECHANISM: recursive children walk from the root; folders are
        traversed, files become records. Graph hashes ride in the file
        facet: prefer sha1Hash, fall back to quickXorHash."""
        records = []
        stack = [f"{GRAPH}/me/drive/root/children?$top=200"]
        while stack:
            for item in self._children(stack.pop()):
                if "folder" in item:
                    stack.append(
                        f"{GRAPH}/me/drive/items/{item['id']}/children"
                        "?$top=200")
                elif "file" in item:
                    hashes = (item.get("file") or {}).get("hashes") or {}
                    h = hashes.get("sha1Hash") or hashes.get(
                        "quickXorHash") or ""
                    alg = "sha1" if hashes.get("sha1Hash") else (
                        "quickXor" if h else "")
                    records.append(FileRecord(
                        provider=self.name,
                        id=item["id"],
                        name=item.get("name", ""),
                        size=int(item.get("size", 0) or 0),
                        hash=h, hash_alg=alg,
                        created=item.get("createdDateTime", ""),
                        web_url=item.get("webUrl", ""),
                    ))
        return records

    def download(self, file_id, dest_path):
        body = self._req(
            "GET", f"{GRAPH}/me/drive/items/{file_id}/content", raw=True)
        with open(dest_path, "wb") as fh:
            fh.write(body)

    def trash(self, file_id):
        self._req("DELETE", f"{GRAPH}/me/drive/items/{file_id}", raw=True)
        return True
