from __future__ import annotations

import inspect
import json
from typing import Any, Callable

from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse


class Request:
    def __init__(self, body: bytes = b""):
        self._body = body

    async def json(self) -> Any:
        return json.loads(self._body.decode("utf-8"))


class FastAPI:
    def __init__(self, title: str = "app"):
        self.title = title
        self.routes: dict[tuple[str, str], Callable[..., Any]] = {}

    def get(self, path: str):
        def decorator(func: Callable[..., Any]):
            self.routes[("GET", path)] = func
            return func

        return decorator

    def post(self, path: str):
        def decorator(func: Callable[..., Any]):
            self.routes[("POST", path)] = func
            return func

        return decorator

    async def _execute(self, method: str, path: str, body: bytes = b"") -> Response:
        handler = self.routes.get((method.upper(), path))
        if handler is None:
            return PlainTextResponse("Not Found", status_code=404)

        kwargs: dict[str, Any] = {}
        if "request" in inspect.signature(handler).parameters:
            kwargs["request"] = Request(body)

        result = handler(**kwargs)
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, Response):
            return result
        if isinstance(result, dict):
            return JSONResponse(result)
        return PlainTextResponse(str(result))

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]):
        if scope.get("type") != "http":
            return

        body = b""
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break

        response = await self._execute(scope["method"], scope["path"], body)
        headers = [(b"content-type", response.media_type.encode("utf-8"))]
        for key, value in response.headers.items():
            headers.append((key.encode("utf-8"), value.encode("utf-8")))
        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": headers,
            }
        )

        if isinstance(response, StreamingResponse):
            first_chunk = b""
            async for item in response.stream:
                first_chunk = item.encode("utf-8")
                break
            await send({"type": "http.response.body", "body": first_chunk})
            return

        await send({"type": "http.response.body", "body": response.body})


__all__ = ["FastAPI", "Request", "JSONResponse", "PlainTextResponse", "StreamingResponse"]
