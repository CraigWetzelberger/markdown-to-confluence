"""Confluence REST API v2 client."""

import mimetypes
import os
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth


class ConfluenceClient:
    """Thin wrapper around the Confluence Cloud REST API v2."""

    def __init__(self, base_url: str, username: str, api_token: str, space_key: str):
        """Initialise the client.

        Args:
            base_url:   Your Confluence base URL, e.g. ``https://myorg.atlassian.net/wiki``.
            username:   Atlassian account email address.
            api_token:  Atlassian API token (generate at id.atlassian.com).
            space_key:  The Confluence space key where pages will be created.
        """
        self.base_url = base_url.rstrip("/")
        self.space_key = space_key
        self._auth = HTTPBasicAuth(username, api_token)
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    # ------------------------------------------------------------------
    # Page operations
    # ------------------------------------------------------------------

    def get_page_by_title(self, title: str, parent_id: str | None = None) -> dict | None:
        """Return the first page matching *title* in the configured space, or None."""
        params: dict = {
            "spaceKey": self.space_key,
            "title": title,
            "expand": "version",
        }
        resp = self._session.get(f"{self.base_url}/rest/api/content", params=params)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None

    def create_page(self, title: str, body: str, parent_id: str | None = None) -> dict:
        """Create a new Confluence page and return the API response dict."""
        payload: dict = {
            "type": "page",
            "title": title,
            "space": {"key": self.space_key},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]

        resp = self._session.post(
            f"{self.base_url}/rest/api/content",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def update_page(self, page_id: str, title: str, body: str, version: int) -> dict:
        """Update an existing Confluence page."""
        payload = {
            "type": "page",
            "title": title,
            "version": {"number": version + 1},
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }
        resp = self._session.put(
            f"{self.base_url}/rest/api/content/{page_id}",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def upsert_page(self, title: str, body: str, parent_id: str | None = None) -> dict:
        """Create or update a page with the given title."""
        existing = self.get_page_by_title(title, parent_id)
        if existing:
            version = existing["version"]["number"]
            return self.update_page(existing["id"], title, body, version)
        return self.create_page(title, body, parent_id)

    # ------------------------------------------------------------------
    # Attachment operations
    # ------------------------------------------------------------------

    def upload_attachment(self, page_id: str, file_path: str) -> dict:
        """Upload a file as an attachment to a Confluence page."""
        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"

        existing_url = f"{self.base_url}/rest/api/content/{page_id}/child/attachment"
        check = self._session.get(existing_url, params={"filename": filename})
        check.raise_for_status()
        existing = check.json().get("results", [])

        with open(file_path, "rb") as fh:
            files = {"file": (filename, fh, mime_type)}
            headers = {"X-Atlassian-Token": "no-check"}

            if existing:
                attach_id = existing[0]["id"]
                url = f"{existing_url}/{attach_id}/data"
            else:
                url = existing_url

            # Remove Content-Type from session headers for multipart upload
            session_ct = self._session.headers.pop("Content-Type", None)
            resp = self._session.post(url, files=files, headers=headers)
            if session_ct:
                self._session.headers["Content-Type"] = session_ct

        resp.raise_for_status()
        return resp.json()
