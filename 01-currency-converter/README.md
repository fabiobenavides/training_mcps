# 01 — Currency Converter (MCP)

Local MCP lab: a Python **stdio server** and a Python **client** that launches it as a subprocess and calls its tools over MCP.

```text
01-currency-converter/
  server/     # MCP server (tools)
  client/     # MCP client (stdio host)
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
cd 01-currency-converter/server
uv sync

cd ../client
uv sync
```

## Server tools

| Tool | Purpose |
| --- | --- |
| `convert_currency` | Convert `amount` from `from_currency` to `to_currency` |
| `list_rates` | List supported currencies and rates vs USD |

Supported currencies: `USD`, `EUR`, `MXN`, `COP`.

## Run the Python client

From the client folder:

```bash
cd 01-currency-converter/client
uv run python client.py
```

The client will:

1. Start `../server/server.py` over **stdio** (`uv run` when available).
2. Call `tools/list`.
3. Call `list_rates`.
4. Convert `50 USD -> MXN`.
5. Call `convert_currency` with an invalid currency and print the error.

## Optional: Cursor as another client

[`mcp.example.json`](mcp.example.json) shows how to register the same server in Cursor MCP settings. This lab’s primary client is the Python script above.

## Notes

- Rates are hardcoded for learning; they are **not** live market data.
- Do not write to **stdout** in the server process. MCP uses stdio as the wire protocol; use `logging` (stderr) instead.
