# structured-data-core

Deterministic, stateless structured-data quality service with FastAPI and minimal MCP-style JSON-RPC.

## Runtime

- Python 3.11
- FastAPI
- Uvicorn

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Render (Free tier)

`render.yaml` is included.
Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## HTTP endpoints

- `GET /health` -> `{"status":"ok"}`
- `GET /privacy` -> placeholder text
- `GET /support` -> placeholder text with support email
- `GET /terms` -> placeholder text
- `GET /mcp` -> MCP manifest with tool metadata
- `GET /sse` -> basic SSE event stream
- `POST /message` -> JSON-RPC 2.0

## JSON-RPC methods

- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`

## tools/list response

Exactly five tools are returned, each with governance risk flags (`readOnlyHint=true`, `openWorldHint=false`, `destructiveHint=false`):

1. `data_validate`
2. `data_normalize`
3. `data_fill_defaults`
4. `data_map_fields`
5. `data_pick_fields`

## tools/call examples

### 1) data_validate

Request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "data_validate",
    "arguments": {
      "rules": {
        "required": ["a", "b"],
        "type": {"a": "string", "b": "integer"},
        "enum": {"status": ["new", "ok", "bad"]}
      },
      "data": {"a": "x", "b": 2, "status": "ok"}
    }
  }
}
```

### 2) data_normalize

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "data_normalize",
    "arguments": {
      "data": {"name": "  Alice   Smith  ", "meta": {"city": "  New   York"}},
      "options": {"trim_strings": true, "collapse_spaces": true, "remove_empty_strings": false}
    }
  }
}
```

### 3) data_fill_defaults

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "data_fill_defaults",
    "arguments": {
      "data": {"a": 1, "b": null},
      "defaults": {"b": 2, "c": 3}
    }
  }
}
```

### 4) data_map_fields

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "data_map_fields",
    "arguments": {
      "data": {"oldField": 1, "a": {"b": "x"}},
      "mapping": {"oldField": "newField", "a.b": "c.d"}
    }
  }
}
```

### 5) data_pick_fields

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "data_pick_fields",
    "arguments": {
      "data": {"a": 1, "b": 2, "c": {"d": 3, "e": 4}},
      "fields": ["a", "c.d"]
    }
  }
}
```

## Error contract

When params are invalid, JSON-RPC returns:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "issues": [
        {"path": "data", "code": "type", "message": "data must be an object"}
      ]
    }
  }
}
```


## SSE behavior

- `GET /sse` returns `text/event-stream` with `Cache-Control: no-cache` and `Connection: keep-alive`.
- First event is immediate: `event: connected` with JSON `session_id` (UUID4).
- Keepalive comment ping is emitted every 15 seconds as `: ping`.

- `/mcp` manifest includes `base_url` for MCP discovery.
