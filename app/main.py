from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse

from app.mcp import MCP_MANIFEST, handle_rpc


class Response:
    def __init__(self, status_code: int = 200, body: bytes = b"", content_type: str = "text/plain", headers: dict[str, str] | None = None):
        self.status_code = status_code
        self.body = body
        self.content_type = content_type
        self.headers = headers or {}

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self):
        return json.loads(self.text)


class StreamingResponse(Response):
    def __init__(self, stream: AsyncGenerator[str, None], content_type: str, headers: dict[str, str]):
        super().__init__(status_code=200, body=b"", content_type=content_type, headers=headers)
        self.stream = stream


class App:
    def __init__(self):
        self.routes: dict[tuple[str, str], callable] = {}

    def get(self, path: str):
        def deco(fn):
            self.routes[("GET", path)] = fn
            return fn

        return deco

    def post(self, path: str):
        def deco(fn):
            self.routes[("POST", path)] = fn
            return fn

        return deco

    async def dispatch(self, method: str, url: str, body: bytes = b"") -> Response:
        parsed = urlparse(url)
        fn = self.routes.get((method.upper(), parsed.path))
        if fn is None:
            return Response(status_code=404, body=b"Not Found")
        query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        return await fn(body=body, query=query)


app = App()


@app.get("/health")
async def health(body: bytes = b"", query: dict[str, str] | None = None) -> Response:
    return Response(body=json.dumps({"status": "ok"}).encode(), content_type="application/json")


@app.get("/privacy")
async def privacy(body: bytes = b"", query: dict[str, str] | None = None) -> Response:
    return Response(body=b"Privacy placeholder")


@app.get("/terms")
async def terms(body: bytes = b"", query: dict[str, str] | None = None) -> Response:
    return Response(body=b"Terms placeholder")


@app.get("/support")
async def support(body: bytes = b"", query: dict[str, str] | None = None) -> Response:
    return Response(body=b"support@example.com")


@app.get("/.well-known/openai-apps-challenge")
async def openai_apps_challenge(body: bytes = b"", query: dict[str, str] | None = None) -> Response:
    return Response(body=b"challenge-placeholder")


@app.get("/mcp")
async def mcp(body: bytes = b"", query: dict[str, str] | None = None) -> Response:
    return Response(body=json.dumps(MCP_MANIFEST).encode(), content_type="application/json")


@app.post("/message")
async def message(body: bytes = b"", query: dict[str, str] | None = None) -> Response:
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return Response(body=json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}).encode(), content_type="application/json")

    session_id = (query or {}).get("sessionId")
    out = handle_rpc(payload, session_id=session_id)
    if out is None:
        return Response(status_code=204, body=b"", content_type="application/json")
    return Response(body=json.dumps(out).encode(), content_type="application/json")


@app.get("/sse")
async def sse(body: bytes = b"", query: dict[str, str] | None = None) -> StreamingResponse:
    session_id = str(uuid.uuid4())

    async def stream() -> AsyncGenerator[str, None]:
        _ = time.monotonic()
        yield f"event: connected\ndata: {json.dumps({'session_id': session_id})}\n\n"
        while True:
            await asyncio.sleep(15)
            yield ": ping\n\n"

    return StreamingResponse(
        stream=stream(),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
