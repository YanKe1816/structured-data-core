# CAPABILITIES

## Deterministic structured-data tools

- `data_validate`: required/type/enum checks with deterministic issue list output.
- `data_normalize`: trim/collapse/remove-empty-string normalization with change tracking.
- `data_fill_defaults`: fills missing/null top-level fields from defaults.
- `data_map_fields`: deterministic field moves using dot-path mapping.
- `data_pick_fields`: deterministic projection using explicit field paths.

## Service constraints

- Stateless request handling.
- No external network reads/writes.
- JSON-RPC 2.0 with stable error format.
- FastAPI HTTP + minimal SSE endpoint.
