"""HTTP client for Weezdom.ai REST API."""

import httpx

from weezdom_cli import config


_UNSET = object()


class WeezdomClient:
    """Thin httpx wrapper that attaches auth and graph headers."""

    def __init__(self, api_url: str = None, api_key: str = None, graph_id: str = _UNSET):
        cfg = config.load()
        self.api_url = (api_url or cfg.get("api_url", "")).rstrip("/")
        self.api_key = api_key or cfg.get("api_key")
        self.graph_id = cfg.get("active_graph_id") if graph_id is _UNSET else graph_id

    def _headers(self) -> dict:
        h = {}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        if self.graph_id:
            h["X-Graph-Id"] = self.graph_id
        return h

    def _handle_error(self, resp: httpx.Response):
        if resp.status_code == 401:
            raise click_exit("Not authenticated. Run: weezdom auth login")
        if resp.status_code == 403:
            raise click_exit("Access denied. Check your permissions.")
        if resp.status_code == 404:
            if resp.headers.get("content-type", "").startswith("application/json"):
                detail = resp.json().get("detail", f"Not found: {resp.url.path}")
            else:
                detail = f"Not found: {resp.url.path}"
            raise click_exit(detail)
        if resp.status_code >= 400:
            if resp.headers.get("content-type", "").startswith("application/json"):
                detail = resp.json().get("detail", resp.text[:200])
            else:
                detail = resp.text[:200]  # truncate to avoid leaking full proxy/server error bodies
            raise click_exit(f"API error ({resp.status_code}): {detail}")

    async def get(self, path: str, params: dict = None) -> dict:
        async with httpx.AsyncClient(base_url=self.api_url, headers=self._headers(), timeout=30) as c:
            resp = await c.get(path, params=params)
            self._handle_error(resp)
            return resp.json()

    async def post(self, path: str, json: dict = None, data=None, files=None) -> dict:
        async with httpx.AsyncClient(base_url=self.api_url, headers=self._headers(), timeout=30) as c:
            resp = await c.post(path, json=json, data=data, files=files)
            self._handle_error(resp)
            return resp.json()

    async def delete(self, path: str) -> dict:
        async with httpx.AsyncClient(base_url=self.api_url, headers=self._headers(), timeout=30) as c:
            resp = await c.delete(path)
            self._handle_error(resp)
            return resp.json()

    async def validate_auth(self) -> dict:
        """Validate API key against /auth/me. Returns user info or raises."""
        return await self.get("/auth/me")


class ClickExit(Exception):
    """Raised to exit with a user-friendly message."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def click_exit(message: str) -> ClickExit:
    return ClickExit(message)
