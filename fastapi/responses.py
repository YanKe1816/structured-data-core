from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any


class Response:
    def __init__(
        self,
        content: Any = b"",
        status_code: int = 200,
        media_type: str = "text/plain",
        headers: dict[str, str] | None = None,
    ):
        if isinstance(content, bytes):
            body = content
        elif isinstance(content, str):
            body = content.encode("utf-8")
        else:
            body = str(content).encode("utf-8")
        self.body = body
        self.status_code = status_code
        self.media_type = media_type
        self.headers = headers or {}


class JSONResponse(Response):
    def __init__(self, content: Any, status_code: int = 200, headers: dict[str, str] | None = None):
        super().__init__(json.dumps(content), status_code=status_code, media_type="application/json", headers=headers)


class PlainTextResponse(Response):
    def __init__(self, content: str, status_code: int = 200, headers: dict[str, str] | None = None):
        super().__init__(content, status_code=status_code, media_type="text/plain", headers=headers)


class StreamingResponse(Response):
    def __init__(
        self,
        content: AsyncGenerator[str, None],
        status_code: int = 200,
        media_type: str = "text/plain",
        headers: dict[str, str] | None = None,
    ):
        super().__init__(b"", status_code=status_code, media_type=media_type, headers=headers)
        self.stream = content
