from __future__ import annotations

from typing import Any

import requests


class ZengineError(RuntimeError):
    pass


class ZengineClient:
    def __init__(
        self,
        api_token: str,
        base_url: str = "https://api.zenginehq.com/v1",
        timeout_seconds: int = 60,
    ) -> None:
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def get_form(self, form_id: int) -> dict[str, Any]:
        return self._get(f"/forms/{form_id}.json")

    def get_records(
        self,
        form_id: int,
        *,
        page: int = 1,
        limit: int = 100,
        sort: str = "modified",
        direction: str = "desc",
    ) -> dict[str, Any]:
        return self._get(
            f"/forms/{form_id}/records",
            params={
                "page": page,
                "limit": limit,
                "sort": sort,
                "direction": direction,
            },
        )

    def iter_records(
        self,
        form_id: int,
        *,
        max_pages: int,
        limit: int = 100,
        sort: str = "modified",
        direction: str = "desc",
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            payload = self.get_records(
                form_id,
                page=page,
                limit=limit,
                sort=sort,
                direction=direction,
            )
            page_records = payload.get("data", [])
            if not isinstance(page_records, list) or not page_records:
                break
            records.extend(page_records)
            total_count = int(payload.get("totalCount", 0) or 0)
            if total_count and len(records) >= total_count:
                break
            if len(page_records) < limit:
                break
        return records

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_params = dict(params or {})
        request_params["access_token"] = self.api_token
        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}",
                params=request_params,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise ZengineError("Could not reach the Zengine API.") from exc
        if not response.ok:
            raise ZengineError(_format_error(response))
        try:
            payload = response.json()
        except ValueError as exc:
            raise ZengineError("Zengine returned a non-JSON response.") from exc
        if not isinstance(payload, dict):
            raise ZengineError("Zengine returned an unexpected response shape.")
        return payload


def _format_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        for key in ("message", "error", "errors"):
            value = payload.get(key)
            if value:
                return f"Zengine API error {response.status_code}: {value}"
    text = response.text.strip()
    if text:
        return f"Zengine API error {response.status_code}: {text[:500]}"
    return f"Zengine API error {response.status_code}."
