# 02 — Currency Converter (FastMCP)

Local MCP lab: a Python **stdio server** built with the standalone [`fastmcp`](https://github.com/PrefectHQ/fastmcp) package, plus a Python **client** that launches it as a subprocess and calls its tools over MCP.

Compared with [01-currency-converter](../01-currency-converter):

| Lab | Server API | Package |
| --- | --- | --- |
| 01 | `MCPServer` | Official SDK `mcp` (v2 renamed FastMCP → MCPServer) |
| 02 | `FastMCP` | Standalone `fastmcp` (Prefect) |

```text
02-currency-converter-fastmcp/
  server/     # FastMCP server (tools)
  client/     # MCP client (stdio host)
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
cd 02-currency-converter-fastmcp/server
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
cd 02-currency-converter-fastmcp/client
uv run python client.py
```

### If `uv` is not recognized (Windows)

`uv` installs to `%USERPROFILE%\.local\bin`. That folder is on your user `PATH`, but **terminals opened before the install** will not see it yet.

Refresh PATH in the current PowerShell session:

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv run python .\client.py
```

Or open a **new** terminal and run `uv` again.

Without `uv` (after `uv sync` has already created `.venv`):

```powershell
.\.venv\Scripts\python.exe .\client.py
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
