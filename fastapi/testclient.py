from __future__ import annotations

import asyncio
import json
from typing import Any


class _ClientResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8"))

    @property
    def text(self) -> str:
        return self._body.decode("utf-8")


class TestClient:
    def __init__(self, app):
        self.app = app

    def request(self, method: str, path: str, json: dict[str, Any] | None = None):
        async def runner():
            request_body = b""
            if json is not None:
                request_body = __import__("json").dumps(json).encode("utf-8")
            sent_messages: list[dict[str, Any]] = []

            async def receive():
                return {"type": "http.request", "body": request_body, "more_body": False}

            async def send(message: dict[str, Any]):
                sent_messages.append(message)

            scope = {"type": "http", "method": method.upper(), "path": path}
            await self.app(scope, receive, send)
            status = 500
            body = b""
            for message in sent_messages:
                if message["type"] == "http.response.start":
                    status = message["status"]
                if message["type"] == "http.response.body":
                    body = message.get("body", b"")
            return _ClientResponse(status, body)

        return asyncio.run(runner())

    def get(self, path: str):
        return self.request("GET", path)

    def post(self, path: str, json: dict[str, Any] | None = None):
        return self.request("POST", path, json=json)
