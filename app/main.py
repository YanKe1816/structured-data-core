from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from app.mcp import MCP_MANIFEST, handle_rpc

app = FastAPI(title="structured-data-core")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/privacy")
def privacy() -> PlainTextResponse:
    return PlainTextResponse("Privacy placeholder: this demo service processes data in-memory only.")


@app.get("/terms")
def terms() -> PlainTextResponse:
    return PlainTextResponse("Terms placeholder: deterministic rule-execution service.")


@app.get("/support")
def support() -> PlainTextResponse:
    return PlainTextResponse("Support placeholder: support@example.com")


@app.get("/mcp")
def mcp_manifest() -> JSONResponse:
    return JSONResponse(MCP_MANIFEST)


@app.post("/message")
async def message(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
        )

    response = handle_rpc(body)
    if response is None:
        return JSONResponse(status_code=204, content={})
    return JSONResponse(response)


@app.get("/sse")
async def sse() -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[str, None]:
        yield ":ok\n\n"
        while True:
            await asyncio.sleep(12)
            yield ":keepalive\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
