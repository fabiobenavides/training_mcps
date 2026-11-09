# 04 — Currency Converter (LangChain + MCP)

Local MCP lab: the same FastMCP **currency-converter** server as [02](../02-currency-converter-fastmcp) / [03](../03-currency-converter-cursor-sdk), driven by a **LangChain** agent (`MCPAdapter` + `create_agent`).

Here **LangChain** owns the tool loop. The model is a normal chat LLM, so swapping providers is mostly a model-string / dependency change — unlike lab 03, where Cursor SDK is a full agent runtime, not a drop-in LangChain chat model.

```text
04-currency-converter-langchain/
  server/     # FastMCP server (tools)
  client/     # LangChain MCPAdapter + create_agent
```

Compared with earlier labs:

| Lab | Who calls tools | LLM layer |
| --- | --- | --- |
| 01 / 02 | Scripted MCP client | none |
| 03 | Cursor agent | Cursor SDK (`composer-2.5`) |
| **04** | LangChain agent | Interchangeable (`LAB_MODEL`) |

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- An LLM API key for whichever provider you set in `LAB_MODEL`

## Setup

```bash
cd 04-currency-converter-langchain/server
uv sync

cd ../client
uv sync
```

### Recommended (free): Google Gemini

Get a key at [Google AI Studio](https://aistudio.google.com/apikey) (free tier; rate-limited).

```powershell
cd 04-currency-converter-langchain\client
uv sync

$env:GOOGLE_API_KEY = "AIza..."
$env:LAB_MODEL = "google_genai:gemini-3.5-flash-lite"
```

Use the `google_genai:` prefix. A bare `gemini-...` id can resolve to Vertex AI instead of the Gemini Developer API.

Other free Flash ids to try: `google_genai:gemini-3.6-flash`, `google_genai:gemini-3.8-flash`. Older ids such as `gemini-2.5-flash` often return `404 NOT_FOUND` for new API keys.

After `tools/list`, the client calls Gemini. A long pause there is the **LLM HTTP request**, not MCP. Free tier frequently returns **`503 UNAVAILABLE`**, **`504 DEADLINE_EXCEEDED`**, or hits the 90s local timeout — that is Google capacity, not an MCP bug. The client prints a short `Model call failed: ...` line (no full traceback). Retry later or switch `LAB_MODEL` to another Flash/Lite model.

A console line like `Key 'additionalProperties' is not supported in schema, ignoring` is harmless (Gemini drops that JSON Schema field when binding tools).

### Alternative: OpenAI

Default in code if `LAB_MODEL` is unset: `openai:gpt-4.1-mini` (`langchain-openai` is already a dependency).

```powershell
$env:OPENAI_API_KEY = "sk-..."
# optional; this is already the default
$env:LAB_MODEL = "openai:gpt-4.1-mini"
```

Requires billed OpenAI credits. A `429` / “no credits remaining” error is a billing issue, not an MCP bug.

## Server tools

| Tool | Purpose |
| --- | --- |
| `convert_currency` | Convert `amount` from `from_currency` to `to_currency` |
| `list_rates` | List supported currencies and rates vs USD |

Supported currencies: `USD`, `EUR`, `MXN`, `COP`.

## Run the LangChain client

```bash
cd 04-currency-converter-langchain/client
uv run python client.py
```

### If `uv` is not recognized (Windows)

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
uv run python .\client.py
```

The client will:

1. Launch `../server/server.py` over **stdio** via `MCPAdapter` (`mcpServers` config).
2. Print discovered tools.
3. Build `create_agent(model, tools, ...)`.
4. Ask to convert `50 USD -> MXN`.
5. Call the LLM (this is where free-tier Gemini may stall).
6. Print the agent transcript (including tool calls / tool results when present).

## Changing the LLM

This lab uses the current LangChain MCP API (`langchain.mcp.MCPAdapter`), **not** the legacy `langchain-mcp-adapters` / `MultiServerMCPClient` package.

`LAB_MODEL` is a `provider:model` string. To switch providers:

1. Add the provider package if needed (Gemini is already listed; for others e.g. `uv add langchain-anthropic`).
2. Set `LAB_MODEL` (e.g. `google_genai:gemini-3.8-flash`, `anthropic:claude-sonnet-4-5`).
3. Export that provider’s API key (`GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, …).

The client only requires `OPENAI_API_KEY` when `LAB_MODEL` starts with `openai:`.

Cursor SDK / `CURSOR_API_KEY` is **not** a LangChain chat model — keep Cursor integrations in lab 03.

## Optional: Cursor IDE as another client

[`mcp.example.json`](mcp.example.json) shows how to register the same server in Cursor MCP settings. This lab’s primary client is the LangChain script above.

## Notes

- Rates are hardcoded for learning; they are **not** live market data.
- Do not write to **stdout** in the server process. MCP uses stdio as the wire protocol; use `logging` (stderr) instead.
- `langchain.mcp` is marked beta in LangChain ≥ 1.4; the API may evolve.
- Gemini free-tier prompts may be used by Google to improve products (see their terms); avoid sensitive data.
