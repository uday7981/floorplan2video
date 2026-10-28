"""Supabase Storage REST wrapper: signed URLs, upload, download, delete.

The service-role key is required (sits in the Authorization header). Buckets
must exist in advance (created by seed script or supabase CLI).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class SignedUrl:
    url: str
    path: str
    expires_in_s: int


class Storage:
    def __init__(self, supabase_url: str, service_role_key: str,
                 *, client: httpx.Client | None = None):
        self.base = f"{supabase_url.rstrip('/')}/storage/v1"
        self.key = service_role_key
        self._client = client or httpx.Client(
            headers={"Authorization": f"Bearer {service_role_key}",
                     "apikey": service_role_key},
            timeout=30.0,
        )

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    # ---- signed upload ----

    def create_signed_upload_url(self, bucket: str, path: str) -> SignedUrl:
        """Returns a URL + token the client can PUT to directly."""
        r = self._client.post(self._url(f"/object/upload/sign/{bucket}/{path}"))
        r.raise_for_status()
        data = r.json()
        # Response shape: {"url": "/object/upload/sign/...", "token": "..."}
        return SignedUrl(
            url=f"{self.base}{data['url']}" if data["url"].startswith("/") else data["url"],
            path=path,
            expires_in_s=3600,
        )

    # ---- signed read ----

    def create_signed_read_url(self, bucket: str, path: str,
                               expires_in_s: int = 3600) -> SignedUrl:
        r = self._client.post(
            self._url(f"/object/sign/{bucket}/{path}"),
            json={"expiresIn": expires_in_s},
        )
        r.raise_for_status()
        data = r.json()
        signed = data.get("signedURL") or data.get("signedUrl") or ""
        return SignedUrl(
            url=f"{self.base}{signed}" if signed.startswith("/") else signed,
            path=path,
            expires_in_s=expires_in_s,
        )

    # ---- direct uploads (used by workers that already have the bytes) ----

    def upload(self, bucket: str, path: str, body: bytes,
               content_type: str = "application/octet-stream") -> None:
        r = self._client.post(
            self._url(f"/object/{bucket}/{path}"),
            content=body,
            headers={"Content-Type": content_type,
                     "x-upsert": "true"},
        )
        r.raise_for_status()

    def download(self, bucket: str, path: str) -> bytes:
        r = self._client.get(self._url(f"/object/{bucket}/{path}"))
        r.raise_for_status()
        return r.content

    def delete(self, bucket: str, paths: list[str]) -> None:
        r = self._client.request(
            "DELETE", self._url(f"/object/{bucket}"),
            json={"prefixes": paths},
        )
        r.raise_for_status()


def storage_from_config(cfg) -> Storage:
    return Storage(cfg.supabase_url, cfg.supabase_service_role_key)
