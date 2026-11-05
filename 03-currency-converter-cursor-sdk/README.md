# 03 — Currency Converter (Cursor SDK + MCP)

Local MCP lab: the same FastMCP **currency-converter** server as [02](../02-currency-converter-fastmcp), driven by a **Cursor SDK** agent instead of a scripted MCP client.

Cursor runs the agent loop: you pass a natural-language prompt and register the server via `mcp_servers`; the agent decides whether to call `list_rates` / `convert_currency`. The client streams `tool_call` events and the final assistant text.

```text
03-currency-converter-cursor-sdk/
  server/     # FastMCP server (tools)
  client/     # Cursor SDK agent (local + stdio MCP)
```

Compared with earlier labs:

| Lab | Who calls tools |
| --- | --- |
| 01 / 02 | Python client (`list_tools` / `call_tool`) |
| **03** | Cursor agent (`Agent.create` + inline MCP) |
| 04 | LangChain `create_agent` + `MCPAdapter` |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A Cursor API key (`CURSOR_API_KEY`) from [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations)

## Setup

```bash
cd 03-currency-converter-cursor-sdk/server
uv sync

cd ../client
uv sync
```

Export your key (PowerShell):

```powershell
$env:CURSOR_API_KEY = "cursor_..."
```

## Server tools

| Tool | Purpose |
| --- | --- |
| `convert_currency` | Convert `amount` from `from_currency` to `to_currency` |
| `list_rates` | List supported currencies and rates vs USD |

Supported currencies: `USD`, `EUR`, `MXN`, `COP`.

## Run the Cursor SDK client

```bash
cd 03-currency-converter-cursor-sdk/client
uv run python client.py
```

### If `uv` is not recognized (Windows)

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv run python .\client.py
```

The client will:

1. Start `../server/server.py` as an inline **stdio** MCP server for a local Cursor agent.
2. Send a fixed prompt: convert `50 USD -> MXN` using MCP tools.
3. Print streamed `tool_call` events (name, status, args/result) and assistant text.
4. Exit `0` on success, `1` if the run never started (`CursorAgentError`), `2` if the run failed after start.

## Optional: Cursor IDE as another client

[`mcp.example.json`](mcp.example.json) shows how to register the same server in Cursor MCP settings. This lab’s primary client is the Cursor SDK script above.

## Notes

- Rates are hardcoded for learning; they are **not** live market data.
- Do not write to **stdout** in the server process. MCP uses stdio as the wire protocol; use `logging` (stderr) instead.
- This lab uses a **local** agent only (no cloud). Model: `composer-2.5`.
- You do **not** implement the tool loop yourself — that is Cursor’s job. LangChain is the wrong abstraction for calling the Cursor Agent API.
